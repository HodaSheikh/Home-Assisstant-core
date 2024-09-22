"""BleBox cover entity."""

from __future__ import annotations

from typing import Any

from blebox_uniapi.box import Box
import blebox_uniapi.cover
from blebox_uniapi.cover import BleboxCoverState

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_CLOSED, STATE_CLOSING, STATE_OPEN, STATE_OPENING
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PRODUCT
from .entity import BleBoxEntity

BLEBOX_TO_COVER_DEVICE_CLASSES = {
    "gate": CoverDeviceClass.GATE,
    "gatebox": CoverDeviceClass.DOOR,
    "shutter": CoverDeviceClass.SHUTTER,
}

BLEBOX_TO_HASS_COVER_STATES = {
    None: None,
    # all blebox covers
    BleboxCoverState.MOVING_DOWN: STATE_CLOSING,
    BleboxCoverState.MOVING_UP: STATE_OPENING,
    BleboxCoverState.MANUALLY_STOPPED: STATE_OPEN,
    BleboxCoverState.LOWER_LIMIT_REACHED: STATE_CLOSED,
    BleboxCoverState.UPPER_LIMIT_REACHED: STATE_OPEN,
    # extra states of gateController product
    BleboxCoverState.OVERLOAD: STATE_OPEN,
    BleboxCoverState.MOTOR_FAILURE: STATE_OPEN,
    BleboxCoverState.SAFETY_STOP: STATE_OPEN,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a BleBox entry."""
    product: Box = hass.data[DOMAIN][config_entry.entry_id][PRODUCT]
    entities = [
        BleBoxCoverEntity(feature) for feature in product.features.get("covers", [])
    ]
    async_add_entities(entities, True)


class BleBoxCoverEntity(BleBoxEntity[blebox_uniapi.cover.Cover], CoverEntity):
    """Representation of a BleBox cover feature."""

    def __init__(self, feature: blebox_uniapi.cover.Cover) -> None:
        """Initialize a BleBox cover feature."""
        super().__init__(feature)
        self._attr_device_class = BLEBOX_TO_COVER_DEVICE_CLASSES[feature.device_class]
        self._attr_supported_features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
        )
        if feature.is_slider:
            self._attr_supported_features |= CoverEntityFeature.SET_POSITION

        if feature.has_stop:
            self._attr_supported_features |= CoverEntityFeature.STOP

        if feature.has_tilt:
            self._attr_supported_features |= (
                CoverEntityFeature.SET_TILT_POSITION
                | CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
            )

    @property
    def current_cover_position(self) -> int | None:
        """Return the current cover position."""
        position = self._feature.current
        if position == -1:  # possible for shutterBox
            return None

        return None if position is None else 100 - position

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Return the current tilt of shutter."""
        position = self._feature.tilt_current
        return None if position is None else 100 - position

    @property
    def is_opening(self) -> bool | None:
        """Return whether cover is opening."""
        return self._is_state(STATE_OPENING)

    @property
    def is_closing(self) -> bool | None:
        """Return whether cover is closing."""
        return self._is_state(STATE_CLOSING)

    @property
    def is_closed(self) -> bool | None:
        """Return whether cover is closed."""
        return self._is_state(STATE_CLOSED)

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Fully open the cover position."""
        await self._feature.async_open()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Fully close the cover position."""
        await self._feature.async_close()

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Fully open the cover tilt."""
        await self._feature.async_set_tilt_position(0)

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Fully close the cover tilt."""
        # note: values are reversed
        await self._feature.async_set_tilt_position(100)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set the cover position."""
        position = kwargs[ATTR_POSITION]
        await self._feature.async_set_position(100 - position)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self._feature.async_stop()

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Set the tilt position."""
        position = kwargs[ATTR_TILT_POSITION]
        await self._feature.async_set_tilt_position(100 - position)

    def _is_state(self, state_name) -> bool | None:
        value = BLEBOX_TO_HASS_COVER_STATES[self._feature.state]
        return None if value is None else value == state_name

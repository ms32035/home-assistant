"""Ubibot sensor."""

from datetime import datetime, timedelta
import json
import logging
import threading

import requests

from homeassistant.components.ubibot import CONF_CHANNEL, CONF_INTERVAL
from homeassistant.const import (
    CONF_API_KEY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_TEMPERATURE,
    TEMP_CELSIUS,
)
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    "temperature": [
        TEMP_CELSIUS,
        "mdi:thermometer",
        DEVICE_CLASS_TEMPERATURE,
        "field1",
    ],
    "humidity": ["%", "mdi:water-percent", DEVICE_CLASS_HUMIDITY, "field2"],
    "lux": ["lx", "mdi:lightbulb-on-outline", DEVICE_CLASS_ILLUMINANCE, "field3"],
}


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Ubibot sensor setup."""

    api_key = config.get(CONF_API_KEY)
    channel = config.get(CONF_CHANNEL)
    refresh_interval = config.get(CONF_INTERVAL, 600)

    ubibot_data = UbibotData(api_key, channel, refresh_interval)

    for t in SENSOR_TYPES.keys():
        add_devices([UbibotSensor(t, channel, ubibot_data)])


class UbibotSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, type, channel, ubibot_data):
        """Initialize the sensor."""
        self._type = type
        self._channel = channel
        self._ubibot_data = ubibot_data
        self._state = self._ubibot_data.data["channel"]["last_values"][
            SENSOR_TYPES[self._type][3]
        ]["value"]

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Ubibot - {0} - {1}".format(self._channel, self._type)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return SENSOR_TYPES[self._type][2]

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return SENSOR_TYPES[self._type][0]

    @property
    def icon(self):
        """Return the icon."""
        return SENSOR_TYPES[self._type][1]

    def update(self):
        """Fetch new state data for the sensor."""
        self._ubibot_data.update()
        self._state = self._ubibot_data.data["channel"]["last_values"][
            SENSOR_TYPES[self._type][3]
        ]["value"]


class UbibotData:
    """Ubibot data object."""

    URL = "https://api.ubibot.io/channels/{0}?account_key={1}"

    def __init__(self, account_key, channel, refresh_interval):
        """
        Initialize the UniFi Ubibot data object.

        :param account_key: Ubibot Account Key
        :param channel: Channel ID
        :param refresh_interval: refresh interval in seconds
        """
        self.account_key = account_key
        self.channel = channel
        self.refresh_interval = refresh_interval
        self.last_refresh = datetime(2000, 1, 1)
        self.data = None
        self._update_in_progress = threading.Lock()
        self.update()

    def update(self):
        """Get data from Ubibot API."""
        if datetime.now() < self.last_refresh + timedelta(
            seconds=self.refresh_interval
        ) or not self._update_in_progress.acquire(False):
            return
        try:
            url = UbibotData.URL.format(self.channel, self.account_key)
            r = requests.get(url)
            if r.status_code == 200:
                self.data = json.loads(r.text)
                self.data["channel"]["last_values"] = json.loads(
                    self.data["channel"]["last_values"]
                )
            else:
                _LOGGER.error(r.status_code)
            self.last_refresh = datetime.now()
        finally:
            self._update_in_progress.release()

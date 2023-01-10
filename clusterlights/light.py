"""Support for Cluster Lights."""
import logging

import voluptuous as vol

from homeassistant.components.light import (
	ATTR_BRIGHTNESS,
	ATTR_EFFECT,
	PLATFORM_SCHEMA,
	SUPPORT_BRIGHTNESS,
	SUPPORT_EFFECT,
	LightEntity,
)
from .clusterlights import clusterlights
from homeassistant.const import CONF_DEVICES, CONF_NAME
import homeassistant.helpers.config_validation as cv
import homeassistant.util.color as color_util

_LOGGER = logging.getLogger(__name__)

SUPPORT_CLUSTERLIGHTS_LED = SUPPORT_BRIGHTNESS | SUPPORT_EFFECT

# Dictionary of effects (patterns) with their getters and setters
LIGHT_EFFECT_LIST = {
#	Effect				Get function					Set function
	'wave'			:	(lambda bulb: bulb.get_wave(),			lambda bulb: bulb.set_wave(True)),
	'phase'			:	(lambda bulb: bulb.get_phase(),			lambda bulb: bulb.set_phase(True)),
	'phased fade away'	:	(lambda bulb: bulb.get_phased_fade_away(),	lambda bulb: bulb.set_phased_fade_away(True)),
	'phased twinkle'	:	(lambda bulb: bulb.get_phased_twinkle(),	lambda bulb: bulb.set_phased_twinkle(True)),
	'fade away'		:	(lambda bulb: bulb.get_fade_away(),		lambda bulb: bulb.set_fade_away(True)),
	'phased twinkle'	:	(lambda bulb: bulb.get_phased_twinkle(),	lambda bulb: bulb.set_phased_twinkle(True)),
	'fast twinkle'		:	(lambda bulb: bulb.get_fast_twinkle(),		lambda bulb: bulb.set_fast_twinkle(True)),
	'stay on'		:	(lambda bulb: bulb.get_stay_on(),		lambda bulb: bulb.set_stay_on(True)),
}

DEVICE_SCHEMA = vol.Schema({vol.Optional(CONF_NAME): cv.string})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
	{vol.Optional(CONF_DEVICES, default={}): {cv.string: DEVICE_SCHEMA}}
)


def setup_platform(hass, config, add_entities, discovery_info=None):
	"""Set up the cluster lights."""
	lights = []
	for address, device_config in config[CONF_DEVICES].items():
		device = {}
		device["name"] = device_config[CONF_NAME]
		device["address"] = address
		light = ClusterLights(device, hass)
		if light.is_valid:
			lights.append(light)
	
	add_entities(lights, True)


class ClusterLights(LightEntity):
	"""Representation of cluster lights."""
	
	def __init__(self, device, hass):
		"""Initialize the cluster lights."""
	
		self._name = device["name"]
		self._address = device["address"]
		self.is_valid = True
		self._bulb = clusterlights(self._address, hass)
		self._brightness = 0
		self._state = False
		self._effect_list = list(LIGHT_EFFECT_LIST)
		self._effect = 'stay on'
		if self._bulb.connect() is False:
			self.is_valid = False
			_LOGGER.error("Failed to connect to cluster lights %s, %s", self._address, self._name)
			return
	
	@property
	def unique_id(self):
		"""Return the ID of this light."""
		return self._address
	
	@property
	def name(self):
		"""Return the name of the device if any."""
		return self._name
		
	@property
	def effect_list(self):
		"""Return the list of supported effects."""
		return self._effect_list

	@property
	def effect(self):
		"""Return the current effect."""
		return self._effect
	
	@property
	def is_on(self):
		"""Return true if device is on."""
		return self._state
	
	@property
	def brightness(self):
		"""Return the brightness property."""
		return self._brightness
	
	@property
	def supported_features(self):
		"""Return the flag supported features."""
		return SUPPORT_CLUSTERLIGHTS_LED
	
	@property
	def should_poll(self):
		"""Feel free to poll."""
		return True
	
	@property
	def assumed_state(self):
		"""We can report the actual state."""
		return False
	
	def turn_on(self, **kwargs):
		"""Turn the cluster lights on."""
		if self._state == False:
			self._state = True
			self._bulb.on()
	
		brightness = kwargs.get(ATTR_BRIGHTNESS)
	
		if brightness is not None:
			self._brightness = brightness
			self._bulb.set_brightness(brightness)
			
		effect = kwargs.get(ATTR_EFFECT)
		
		if effect is not None:
			self._effect = effect
			self._bulb.reset_pattern()
			self.set_effect(effect)
	
	def turn_off(self, **kwargs):
		"""Turn the cluster lights off."""
		self._state = False
		self._bulb.off()
	
	def update(self):
		"""Synchronise internal state with the actual cluster lights state."""
		self._bulb.get_state()
		self._bulb.get_information()
		self._brightness = self._bulb.get_brightness()
		self._state = self._bulb.get_on()
		self._effect = self.get_effect()
	
	def get_effect(self):
		"""Returns the current active effect (pattern)."""
		for effect in LIGHT_EFFECT_LIST:
			if LIGHT_EFFECT_LIST[effect][0](self._bulb):
				return effect
		return 'stay on' # Something went wrong
	
	def set_effect(self, effect):
		"""Sets the current effect (pattern)."""
		LIGHT_EFFECT_LIST[effect][1](self._bulb)

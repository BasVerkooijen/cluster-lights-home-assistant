import time
from enum import IntEnum

from bluepy import btle

class Delegate(btle.DefaultDelegate):
	def __init__(self, cluster_lights):
		self.cluster_lights = cluster_lights
		btle.DefaultDelegate.__init__(self)
	
	def handleNotification(self, cHandle, data):
		"""Handle notifications from state handle."""
		if len(data) <= 5:		# Power response (off() and on())
			power = bool(data[3])
			self.cluster_lights.set_recv_state(power)
		elif len(data) >= 18:	# Status response (get_information())
			brightness = int(data[3])
			pattern = int(data[17])
			self.cluster_lights.set_recv_brightness(brightness)
			self.cluster_lights.set_recv_pattern(pattern)

class clusterlights:
	"""
	This class represents the cluster lights.
	
	Cluster lights offer regular light functionality.
	Cluster lights can be turned on and off and a brightness can be set.
	
	Additionally a selection of patterns can be enabled for which the
	cluster lights will loop through.
	"""
	class Pattern(IntEnum):
		"""Pattern (light effect) bitflags."""
		STAY_OFF			= 0x00
		WAVE				= 0x01
		PHASE				= 0x02
		PHASED_FADE_AWAY	= 0x04
		PHASED_TWINKLE		= 0x08
		FADE_AWAY			= 0x10
		FAST_TWINKLE		= 0x20
		STAY_ON				= 0x40
	
	def __init__(self, mac):
		"""Initialize the cluster lights."""
		self.mac = mac
		
	def set_recv_pattern(self, pattern):
		"""Handle receiving the pattern byte."""
		self.pattern = pattern
		
	def set_recv_brightness(self, brightness):
		"""Handle receiving the brightness byte (0 - 99)."""
		self.brightness = self._translate(brightness, 0, 99, 0, 255)

	def set_recv_state(self, power):
		"""Handle receiving the power state byte."""
		self.power = power

	def connect(self):
		"""Connect to the cluster lights through BLE."""
		self.device = btle.Peripheral(self.mac, addrType=btle.ADDR_TYPE_PUBLIC)
		self.device.setDelegate(Delegate(self))
		
		handles = self.device.getCharacteristics()
		for handle in handles:
			if handle.uuid == "fff1":	# Characterstic which handles commands
				self.controlhandle = handle
			if handle.uuid == "fff4":	# Characteristic which publishes feedback notifications
				self.statehandle = handle
		# Subscribe for notifications
		self.device.writeCharacteristic(self.statehandle.valHandle + 1, b"\x01\x00")
		# Sync the state of the cluster lights
		self.get_state()
		self.get_information()

	def send_packet(self, handle, data):
		"""Send a command to the cluster lights through BLE."""
		initial = time.time()
		while True:
			if time.time() - initial >= 10:
				return False
			try:
				return handle.write(bytes(data), withResponse=False)
			except:
				self.connect()

	def off(self):
		"""Turn off the cluster lights."""
		self.power = False
		packet = bytearray([0x01, 0x01, 0x01, 0x00])
		self.send_packet(self.controlhandle, packet)

	def on(self):
		"""Turn on the cluster lights."""
		self.power = True
		packet = bytearray([0x01, 0x01, 0x01, 0x01])
		self.send_packet(self.controlhandle, packet)

	def set_brightness(self, brightness):
		"""Set the brightness of the cluster lights."""
		self.brightness = brightness
		packet = bytearray([0x03, 0x01, 0x01])
		value = self._translate(brightness, 0, 255, 0, 99)
		packet.append(int(value))
		self.send_packet(self.controlhandle, packet)

	def _translate(self, value, leftMin, leftMax, rightMin, rightMax):
		"""Helper function for mapping values between ranges."""
		# Figure out how 'wide' each range is
		leftSpan = leftMax - leftMin
		rightSpan = rightMax - rightMin

		# Convert the left range into a 0-1 range (float)
		valueScaled = float(value - leftMin) / float(leftSpan)

		# Convert the 0-1 range into a value in the right range.
		return rightMin + (valueScaled * rightSpan)

	def _set_pattern(self, pattern, active):
		"""Activate or deactivate a pattern for the cluster lights."""
		if active:
			self.pattern |= int(pattern)
		else:
			self.pattern &= ~int(pattern)
		packet = bytearray([0x05, 0x01, 0x02, 0x03])
		packet.append(self.pattern)
		self.send_packet(self.controlhandle, packet)
		self.device.waitForNotifications(1.0)

	def set_wave(self, active):
		"""Enable or disable the wave pattern for the cluster lights."""
		self._set_pattern(self.Pattern.WAVE, active)

	def set_phase(self, active):
		"""Enable or disable the phase pattern for the cluster lights."""
		self._set_pattern(self.Pattern.PHASE, active)

	def set_phased_fade_away(self, active):
		"""Enable or disable the phased fade away pattern for the cluster lights."""
		self._set_pattern(self.Pattern.PHASED_FADE_AWAY, active)

	def set_phased_twinkle(self, active):
		"""Enable or disable the phased twinkle pattern for the cluster lights."""
		self._set_pattern(self.Pattern.PHASED_TWINKLE, active)

	def set_fade_away(self, active):
		"""Enable or disable the fade away pattern for the cluster lights."""
		self._set_pattern(self.Pattern.FADE_AWAY, active)

	def set_fast_twinkle(self, active):
		"""Enable or disable the fast twinkle pattern for the cluster lights."""
		self._set_pattern(self.Pattern.FAST_TWINKLE, active)

	def set_stay_on(self, active):
		"""Enable or disable the stay on pattern for the cluster lights."""
		self._set_pattern(self.Pattern.STAY_ON, active)

	def get_state(self):
		"""Updates the state of the cluster lights for get functions."""
		packet = bytearray([0x00]) # Get power state
		self.send_packet(self.controlhandle, packet)
		self.device.waitForNotifications(1.0)

	def get_information(self):
		"""Updates the pattern and brightness information of the cluster lights for get functions."""
		packet = bytearray([0x02, 0x00, 0x01]) # Get lights information
		self.send_packet(self.controlhandle, packet)
		self.device.waitForNotifications(1.0)

	def get_on(self):
		"""Returns the state of the cluster lights."""
		return self.power

	def get_brightness(self):
		"""Returns the brightness of the cluster lights."""
		return self.brightness

	def get_wave(self):
		"""Returns if the wave pattern is active for the cluster lights."""
		return bool(self.pattern & int(self.Pattern.WAVE))

	def get_phase(self):
		"""Returns if the phase pattern is active for the cluster lights."""
		return bool(self.pattern & int(self.Pattern.PHASE))

	def get_phased_fade_away(self):
		"""Returns if the phased fade away pattern is active for the cluster lights."""
		return bool(self.pattern & int(self.Pattern.PHASED_FADE_AWAY))

	def get_phased_twinkle(self):
		"""Returns if the phased twinkle pattern is active for the cluster lights."""
		return bool(self.pattern & int(self.Pattern.PHASED_TWINKLE))

	def get_fade_away(self):
		"""Returns if the fade away pattern is active for the cluster lights."""
		return bool(self.pattern & int(self.Pattern.FADE_AWAY))

	def get_fast_twinkle(self):
		"""Returns if the fast twinkle pattern is active for the cluster lights."""
		return bool(self.pattern & int(self.Pattern.FAST_TWINKLE))

	def get_stay_on(self):
		"""Returns if the stay on pattern is active for the cluster lights."""
		return bool(self.pattern & int(self.Pattern.STAY_ON))

	def get_raw_pattern(self):
		"""Returns the raw pattern byte for the cluster lights containing bit flags for the patterns."""
		return self.pattern

	def reset_pattern(self):
		"""Resets all pattern bitflags internally to be able to set a new pattern. Does not control the cluster lights."""
		self.pattern = self.Pattern.STAY_OFF

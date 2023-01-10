import time
import asyncio
from enum import IntEnum
import threading,queue
from dataclasses import dataclass

from homeassistant.components import bluetooth
from bleak import *

@dataclass
class Packet:
    data: bytearray
    notify: bool
    disconnect: bool # default False

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
		PHASED_FADE_AWAY		= 0x04
		PHASED_TWINKLE			= 0x08
		FADE_AWAY			= 0x10
		FAST_TWINKLE			= 0x20
		STAY_ON				= 0x40
	
	def __init__(self, mac, hass):
		"""Initialize the cluster lights."""
		self.mac = mac
		self.hass = hass
		self.stop = False
		self.brightness = 255
		self.power = False
		self.pattern = self.Pattern.STAY_OFF
		self.comms_loss = False
		self.notify_state_event = asyncio.Event()
		self.notify_info_event = asyncio.Event()
		
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
		"""Starts BLE task to connect and maintain connection"""
		self.task = threading.Thread(target=self.task, args=())
		self.task.start()
		
	def disconnect(self):
		"""Stops BLE task and disconnects from cluster lights"""
		self.stop = True
		self._disconnect()
		self.task.join()
		
	def _disconnect(self):
		"""Puts a special packet in the queue to unblock the task and disconnect"""
		packet = Packet(bytearray([0x00]), False, True)
		self.packets.put(packet)
		
	def task(self):
		"""Runs BLE task to completion, restarts BLE task on unexpected disconnect"""
		self.packets = queue.Queue(maxsize=20)
		
		restart_task = True
		
		while restart_task:
			if self.comms_loss:
				# Retry later
				time.sleep(5)
			
			# Connect and do ble
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)
			loop.run_until_complete(self.ble_task())
			loop.close()
			
			# Connection aborted
			restart_task = self.comms_loss
			# On comms loss, restart connection
		print("Task closed")

	async def ble_task(self):
		"""BLE task"""
#		scanner = bluetooth.async_get_scanner(self.hass)
#		device = await scanner.find_device_by_address(self.mac, timeout=20.0)
		device = bluetooth.async_ble_device_from_address(self.hass, self.mac, connectable=True)
		if device:
			try:
				async with BleakClient(device) as self.device:
					# Connected
					print(f"Connected clusterlights to {self.mac}")
					# Now retrieve the chars and states and enable notifications
					await self._connect()
					#print("Enter ble_main_task loop")
					
					# Enter BLE connection task
					# Loops until user stops AND queue is empty
					while self.stop == False and self.comms_loss is False:
						await self.ble_task_loop()
						
					# End loop
					if not self.comms_loss:
						# Requested disconnect
						await self.device.disconnect()
					print(f"Disconnected clusterlights from {self.mac}")
			except:
				print("Error while connecting, retry in 5s")
				self.comms_loss = True
				pass
		else:
			print(f"Cluster lights {self.mac} could not be found")
			print("Note that the device can only be connected to one client at a time")
			print("Retry in 5s")
			self.comms_loss = True

	async def ble_task_loop(self):
		"""BLE task to keep connection active, handles connection events"""
		packet = self.packets.get() # Blocks task until packet queued
		if not packet.disconnect: # Exception to stop comms
			await self._send_packet(packet)
	
	async def _connect(self):
		"""Connect to the cluster lights through BLE and sync state."""
		self.stop = False
		self.comms_loss = False
		
		services = self.device.services
		for service in services:
			chars = service.characteristics
			for char in chars:
				uuid = char.uuid[4:8] # filter 16-bit uuid from 128-bit uuid
				if uuid == "fff1":	# Characteristic which handles commands
					self.controlhandle = char
				if uuid == "fff4":	# Characteristic which publishes feedback notifications
					self.statehandle = char
		# Subscribe for notifications
		await self.device.start_notify(self.statehandle, self._notification_handler)
		# Sync the state of the cluster lights
		await self._get_state(False)
		await self._get_information(False)
		
	def send_packet(self, data):
		packet = Packet(data, False, False)
		self.packets.put(packet)
		
	async def _send_packet(self, packet):
		"""Send a command to the cluster lights through BLE on control char."""
		try:
			await self.device.write_gatt_char(self.controlhandle, bytes(packet.data), False) # No response
		except Exception as e:
			print("exception occurred at writing characteristic")
			print(f"exception is of type: {type(e)}")
			print(f"Exception detail: {print(e)}")
			print("Attempt to reconnect in 5s")
			self.comms_loss = True
				
	def _notification_handler(self, characteristic, data: bytearray):
		"""Handle notifications from state handle."""
		if len(data) <= 5:	# Power response (off() and on())
			self.notify_state_event.set()
			power = bool(data[3])
			self.set_recv_state(power)
			print("Power notification received")
		elif len(data) >= 18:	# Status response (get_information())
			self.notify_info_event.set()
			brightness = int(data[3])
			pattern = int(data[17])
			self.set_recv_brightness(brightness)
			self.set_recv_pattern(pattern)
			print("Status notification received")

	def off(self):
		"""Turn off the cluster lights."""
		self.power = False
		packet = bytearray([0x01, 0x01, 0x01, 0x00])
		self.send_packet(packet)

	def on(self):
		"""Turn on the cluster lights."""
		self.power = True
		packet = bytearray([0x01, 0x01, 0x01, 0x01])
		self.send_packet(packet)

	def set_brightness(self, brightness):
		"""Set the brightness of the cluster lights."""
		self.brightness = brightness
		packet = bytearray([0x03, 0x01, 0x01])
		value = self._translate(brightness, 0, 255, 0, 99)
		packet.append(int(value))
		self.send_packet(packet)

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
		self.send_packet(packet)
		asyncio.run(self._wait_for_info_notification())
	
	async def _wait_for_info_notification(self):
		"""Wait for info notification received or give up after 1 second"""
		try:
			await asyncio.wait_for(self.notify_info_event.wait(), timeout=1.0)
		except:
			print("No info notification, give up")
			pass

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
		
	async def _get_state(self, wait):
		"""Updates the state of the cluster lights for get functions."""
		packet = bytearray([0x00]) # Get power state
		self.send_packet(packet)
		if wait:
			# Wait for notify received
			try:
				await asyncio.wait_for(self.notify_state_event.wait(), timeout=1.0)
			except:
				print("No state notification, give up")
				pass
		
		
	async def _get_information(self, wait):
		"""Updates the pattern and brightness information of the cluster lights for get functions."""
		packet = bytearray([0x02, 0x00, 0x01]) # Get lights information
		self.send_packet(packet)
		if wait:
			await self._wait_for_info_notification()

	def get_state(self):
		"""Updates the state of the cluster lights for get functions."""
		asyncio.run(self._get_state(True))

	def get_information(self):
		"""Updates the pattern and brightness information of the cluster lights for get functions."""
		asyncio.run(self._get_information(True))

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

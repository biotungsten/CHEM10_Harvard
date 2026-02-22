# This module provides functionality to interface with Arduino boards.

import subprocess
from telemetrix import telemetrix
from pathlib import Path
import json
import numpy as np
import atexit 
import traceback

import sys
import threading
import time
import threading
from CHEM10_Harvard import config

class ArduinoBoard:
    _instances_by_address = {}
    # TODO: reduce wait time for arduino device reset
    def __init__(self, address=None):
        # Register exit hook 
        self.__class__.install_hooks()

        # Set up variables
        self._arduino_board_spec = {"fqbn": "arduino:avr:uno", "address": address}
        self._path_to_telemetrix4arduino = (Path(__file__).resolve().parent / "files" / "Telemetrix4Arduino" )
        self._telemetrix_board = None
        self._assigned_pints = {"digital_output": [], "digital_input": [], "analog_output": [], "analog_input": []}
        
        # This dictionary will hold cached read values and their timestamps for digital and analog pins that were registered as outputs.
        self._read_cache = {"digital": {}, "analog": {}}

        # Get board data and set up arduino-cli
        self._setup_board()

        # Ensure only one instance per address exists
        if self._arduino_board_spec["address"] in self.__class__._instances_by_address:
            raise Exception(f"An ArduinoBoard instance with address {self._arduino_board_spec['address']} already exists.")
        self.__class__._instances_by_address[self._arduino_board_spec["address"]] = self

        # Install Telemetrix4Arduino sketch if not already installed
        self._install_sketch()
    
    @classmethod
    def install_hooks(cls):
        # Register shutdown function to be called at exit
        atexit.register(cls._shutdown_all_boards)

    @classmethod
    def _shutdown_all_boards(cls):
        values = list(cls._instances_by_address.values())
        for val in values:
            val.shutdown()

    # Factory for read callback function
    def _get_read_callback(self):
        def read_callback(data):
            
            if data[0] == config.CB_ANALOG:
                pin_type = "analog"
            elif data[0] == config.CB_DIGITAL:
                pin_type = "digital"
            else:
                print(f"Unknown callback pin mode: {data[0]}")
                return
            pin_number = data[1]
            self._read_cache[pin_type][pin_number][0] = data[2] # Set actual data value
            self._read_cache[pin_type][pin_number][1] = data[3] # Set timestamp
        return read_callback

    def _setup_board(self):
        try:
            # Update arduino-cli core index and install arduino:avr core (it is unproblematic to do this every time)
            subprocess.run(["arduino-cli", "core", "update-index"], check=True)
            subprocess.run(["arduino-cli", "core", "install", "arduino:avr"], check=True)

            # Install Servo library and check that it is installed
            subprocess.run(["arduino-cli", "lib", "install", "Servo"], check=True)
            installed_libraries = subprocess.run(["arduino-cli", "lib", "list"], check=True, text=True, capture_output=True)
            if "Servo" not in installed_libraries.stdout:
                raise Exception("Servo library installation failed.")
            
            # Get a list of connected boards (also includes Bluetooth and other USB devices)
            board_list_result = subprocess.run(
                ["arduino-cli", "board", "list", "--json"], capture_output=True, text=True, check=True
            )
            board_list_dict = json.loads(board_list_result.stdout)
            detected_ports = board_list_dict["detected_ports"]
            
            # Check if any connected ports were detected
            if len(detected_ports) == 0:
                raise Exception("No connected ports found by arduino-cli.")

            # Filter ports to find potential Arduino boards based on hardware_id presence (this excludes unconnected devices)
            arduino_candidates = [p["port"] for p in detected_ports if "hardware_id" in p["port"]]
            if len(arduino_candidates) == 0:
                raise Exception("No connected ports with hardware_id found by arduino-cli.")
            
            # If an address was provided, check that it matches a connected port
            if self._arduino_board_spec["address"] is not None:
                if not any(p["address"] == self._arduino_board_spec["address"] for p in arduino_candidates):
                    raise Exception(f"No connected ports match the provided address ({self._arduino_board_spec['address']}).")
            
            # If no address was provided, handle multiple candidates or select the single candidate
            else:
                if len(arduino_candidates) > 1:
                    print("Warning: Multiple potential Arduino boards detected:\n")
                    for arduino_candidate in arduino_candidates:
                        print(f"Address: {arduino_candidate['address']},  protocol: {arduino_candidate['protocol_label']}, pid: {arduino_candidate['properties']['pid']:#x}, vid: {arduino_candidate['properties']['vid']:#x}\n")
                    print("\n")
                    user_chosen_address = input("Please enter the address of the desired Arduino board (copy from above):").strip()
                    arduino_candidates = [p for p in arduino_candidates if p['address'] == user_chosen_address]
                    if len(arduino_candidates) == 0:
                        raise Exception("No connected ports match the provided address.")
                self._arduino_board_spec["address"] = arduino_candidates[0]['address']
            

        except subprocess.CalledProcessError as e:
            print("Error in arduino-cli:", e)

    def _install_sketch(self):
        # Try to connect to the board; if it fails, compile and upload the Telemetrix4Arduino sketch
        try:
            telemetrix_board = telemetrix.Telemetrix(com_port=self._arduino_board_spec["address"])
        except RuntimeError as e:
            subprocess.run(["arduino-cli", "compile", "--fqbn", self._arduino_board_spec["fqbn"], self._path_to_telemetrix4arduino], check=True)
            subprocess.run(["arduino-cli", "upload", "-p", self._arduino_board_spec["address"], "--fqbn", self._arduino_board_spec["fqbn"], self._path_to_telemetrix4arduino], check=True)
            telemetrix_board = telemetrix.Telemetrix(com_port=self._arduino_board_spec["address"])
        self._telemetrix_board = telemetrix_board
        #TODO: Reset the board (remove all pin modes) after upload

        # Verify that the installed firmware version matches the expected version
        if self._telemetrix_board.firmware_version != config.TELEMETRIX_FIRMWARE_VERSION:
            raise Exception(f"There was a problem installing the Telemetrix4Arduino firmware on the Arduino board. (Firmware {self._telemetrix_board.firmware_version} detected, expected {config.TELEMETRIX_FIRMWARE_VERSION})")

    def analog_read(self, pin, differential=0):
        # I would recommend setting a differential of at least 5 (for the servo that is equivalent to limiting resolution to ~2 degrees) if you don't stabilize the output, to avoid frequent reads that might become a problem since the need to acquire a lock on the telemtrix thread
        # Set pin mode to analog input if not already set
        if pin not in self._assigned_pints["analog_input"]:
            self._assigned_pints["analog_input"].append(pin)
            self._read_cache["analog"][pin] = [None, int(time.time())]
            self._telemetrix_board.set_pin_mode_analog_input(pin, callback=self._get_read_callback(), differential=differential)
            time.sleep(0.1)  # Allow some time for the first reading to be available

        return self._read_cache["analog"][pin][0]

    def digital_read(self, pin, differential=0):
        # Set pin mode to digital input if not already set
        if pin not in self._assigned_pints["digital_input"]:
            self._assigned_pints["digital_input"].append(pin)
            self._read_cache["digital"][pin] = [None, int(time.time())]
            self._telemetrix_board.set_pin_mode_digital_input(pin, callback=self._get_read_callback(), differential=differential)
            time.sleep(0.1)  # Allow some time for the first reading to be available

        return self._read_cache["digital"][pin][0]

    def analog_write(self, pin, value):
        # Set pin mode to analog output if not already set
        if pin not in self._assigned_pints["analog_output"]:
            self._telemetrix_board.set_pin_mode_analog_output(pin)
            self._assigned_pints["analog_output"].append(pin)

        # Ensure value is an integer between 0 and 255
        if not isinstance(value, int):
            print(f"Analog write value must be an integer (not {value}).")
            return -1
        if value < 0 or value > 255:
            print(f"Analog write value must be between 0 and 255 (not {value}).")
            return -1
        
        self._telemetrix_board.analog_write(pin, value)

    def digital_write(self, pin, value):
        # Set pin mode to digital output if not already set
        if pin not in self._assigned_pints["digital_output"]:
            self._telemetrix_board.set_pin_mode_digital_output(pin)
            self._assigned_pints["digital_output"].append(pin)

        # Ensure value is either 0 or 1
        if value not in [0, 1]:
            print(f"Digital write value must be 0 or 1 (not {value}).")
            return -1
        
        self._telemetrix_board.digital_write(pin, value)

    def initialize_servo(self, pin):
        # Specify the control pin of the servo (usually yellow wire)

        # Servo.h library only supports pins 9 and 10 on Arduino Uno
        if pin not in config.SERVO_H_ALLOWED_PINS:
            print(f"Servo control pin must be one of {config.SERVO_H_ALLOWED_PINS} (not {pin}).")
            return -1
        self._telemetrix_board.set_pin_mode_servo(pin, 340, 2275)

    def detach_servo(self, pin):
        # Detach the servo from the control pin
        self._telemetrix_board.servo_detach(pin)

    def write_servo(self, pin, angle):
        # Set the servo to the specified angle (0-180 degrees)
        # Servo behaves non-linearly between inputs of 0-20 degrees. 65 degrees corresponds to actually 90 degrees and 180 degrees corresponds to actually 180 degrees.
        # The file Servo_behavior.png shows the analog readput as a function of servo angle at settings 340, 2275
        # Do not write angle below 10
        if angle < 10 or angle > 180:
            print(f"Servo angle must be between 10 and 180 degrees (not {angle}).")
            return -1
        
        self._telemetrix_board.servo_write(pin, angle)

    def shutdown(self):
        # Shutdown the telemetrix board connection
        if self._telemetrix_board is not None:
            self._telemetrix_board.shutdown()
            self.__class__._instances_by_address.pop(self._arduino_board_spec["address"], None)
            self._telemetrix_board = None

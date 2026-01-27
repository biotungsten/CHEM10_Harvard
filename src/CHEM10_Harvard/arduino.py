# This module provides functionality to interface with Arduino boards.

import subprocess
from telemetrix import telemetrix
from pathlib import Path
import json
import numpy as np
import threading
import config

class ArduinoBoard:
    _instances_by_address = {}

    def __init__(self, address=None):
        self._arduino_board_spec = {"fqbn": "arduino:avr:uno", "address": address}
        self._path_to_telemetrix4arduino = (Path(__file__).resolve().parent / "files" / "Telemetrix4Arduino" )
        self._telemetrix_board = None
        self._setup_board()

        # Ensure only one instance per address exists
        if self._arduino_board_spec["address"] in self.__class__._instances_by_address:
            raise Exception(f"An ArduinoBoard instance with address {self._arduino_board_spec['address']} already exists.")
        self.__class__._instances_by_address[self._arduino_board_spec["address"]] = self

        # Install Telemetrix4Arduino sketch if not already installed
        self._install_sketch()

    def _setup_board(self):
        try:
            # Update arduino-cli core index and install arduino:avr core (it is unproblematic to do this every time)
            subprocess.run(["arduino-cli", "core", "update-index"], check=True)
            subprocess.run(["arduino-cli", "core", "install", "arduino:avr"], check=True)

            # Install Servo library and check that it is installed
            subprocess.run(["arduino-cli", "lib", "install", "\"Servo\""], check=True)
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
            telemetrix_board = telemetrix.TelemetrixBoard(com_port=self._arduino_board_spec["address"])
        except RuntimeError as e:
            subprocess.run(["arduino-cli", "compile", "--fqbn", self._arduino_board_spec["fqbn"], self._path_to_telemetrix4arduino], check=True)
            subprocess.run(["arduino-cli", "upload", "-p", self._arduino_board_spec["address"], "--fqbn", self._arduino_board_spec["fqbn"], self._path_to_telemetrix4arduino], check=True)
            telemetrix_board = telemetrix.TelemetrixBoard(com_port=self._arduino_board_spec["address"])
        self._telemetrix_board = telemetrix_board

        # Verify that the installed firmware version matches the expected version
        if self._telemetrix_board.firmware_version != config.TELEMETRIX_FIRMWARE_VERSION:
            raise Exception(f"There was a problem installing the Telemetrix4Arduino firmware on the Arduino board. (Firmware {self._telemetrix_board.firmware_version} detected, expected {config.TELEMETRIX_FIRMWARE_VERSION})")

    def read(self, pin):
        # Read value from specified pin, by passing to digital_read or analog_read as appropriate
        pass

    def write(self, pin, value):
        # Write value to specified pin, by passing to digital_write or analog_write as appropriate
        pass

    #TODO: Add servo control methods
    # adafru.it/1449

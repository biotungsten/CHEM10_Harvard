# This module provides functionality to interface with Arduino boards.

import subprocess
import telemetrix
import json
import numpy as np

class ArduinoBoard:
    def __init__(self, port=None):
        self._arduino_cli_index_updated = False
        self._arduino_board_spec = {"fqbn": None, "core": None, "name": None}
        # Verify that arduino board is connected (perform auto-detection if port is None)
        # Check whether sketch is running on Arduino 
        # If not, upload sketch to arduino using arduino-cli
        # Initialize telemetrix board
        # Expose digital and analog read/write methods (verify that written port is actually digital/analog)
        # Expose servo control methods
        self._setup_board()
        self._install_sketch()

    def _setup_board(self):
        try: 
            if not self._arduino_cli_index_updated:
                subprocess.run(["arduino-cli", "core", "update-index"], check=True)
                self._arduino_cli_index_updated = True
            board_list_result = subprocess.run(
                ["arduino-cli", "board", "list", "--json"], capture_output=True, text=True, check=True
            )
            #TODO: Check that board_list is not empty
            board_list_dict = json.loads(board_list_result.stdout)
            #TODO: Parse board_list_dict to find the correct board and port, if multiple boards are connected, 
            # throw an error, then store fbqn string and core string in self variables
            # Check that port is the same as port provided (if provided, else store port) or if different overwrite and warn
            #TODO: Check whether core is installed and then install if not
        except subprocess.CalledProcessError as e:
            print("Error in arduino-cli:", e)

    def _install_sketch(self):
        try:
            #TODO: Check whether sketch is running on Arduino by checking whether firmware version is 5.4.4
            # If not running, upload sketch using arduino-cli
            pass
        except subprocess.CalledProcessError as e:
            print("Error in uploading sketch:", e)

    def read(self, pin):
        # Read value from specified pin, by passing to digital_read or analog_read as appropriate
        pass

    def write(self, pin, value):
        # Write value to specified pin, by passing to digital_write or analog_write as appropriate
        pass
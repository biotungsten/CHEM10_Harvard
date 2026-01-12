# This module provides functionality to interface with Arduino boards.

import telemetrix
import numpy as np

class ArduinoBoard:
    def __init__(self, port=None):
        # Verify that arduino board is connected (perform auto-detection if port is None)
        # Check whether sketch is running on Arduino 
        # If not, upload sketch to arduino using arduino-cli
        # Initialize telemetrix board
        # Expose digital and analog read/write methods (verify that written port is actually digital/analog)
        # Expose servo control methods
        pass

    def read(self, pin):
        # Read value from specified pin, by passing to digital_read or analog_read as appropriate
        pass

    def write(self, pin, value):
        # Write value to specified pin, by passing to digital_write or analog_write as appropriate
        pass

    def digital_write(self, pin, value):
        # Write digital value to specified pin, checking pin mode
        pass

    def digital_read(self, pin):
        # Read digital value from specified pin, checking pin mode
        pass

    def analog_write(self, pin, value):
        # Write analog value to specified pin, checking pin mode
        pass

    def analog_read(self, pin):
        # Read analog value from specified pin, checking pin mode
        pass
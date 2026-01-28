# This module contains global configuration settings for the CHEM10 package.

# Firmware version of Telemetrix4Arduino used in CHEM10_Harvard
TELEMETRIX_FIRMWARE_VERSION = [5, 4, 4] 

# Since we are using the Servo.h library under the hood, we need to use pin 9 or 10
SERVO_H_ALLOWED_PINS = [9, 10] 

# Define Telemetrix4Arduino callback pin mode values
CB_DIGITAL = 0
CB_ANALOG = 2
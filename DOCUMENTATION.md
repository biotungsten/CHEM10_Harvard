This document contains the documantation for most of the code. In particular it describes the design choices made and how the package was envisioned to be used. The specific behavior of funcitons is documented in the docstrings. 

# Arduino

# Servo
The specific servo motor the functions were optimized for is a Batan Analog S1123, *for which no datasheet exists*. The range of 0 to 20 degrees was very non-linear in tests. Thus we recommend to only use the servo in the angle range of 30 to 180 degrees. In particular one should **never write an angle below 10 degrees**, as this might break the servo. An angle of 65 degrees corresponds to the actual center position (90 degrees) and 180 degrees corresponds to the maximum position (180 degrees). While a mapping based on these values (analog voltage readouts documented in `Servo_behavior.png`, for parameters 340, 2275) is provided, we recommend having the user perform a calibration for reproducibility.

# Config
The `CB_DIGITAL` and `CB_ANALOG` values deviate from what is in the documentation for Telemetrix but these seem to be correct for firmware version 5.4.4 which is shipped with this package.

# Spectrometer

# Utils

# Testing
We have three sets of tests. The first set of tests checks everything that is purely software side (to the extent that we have testing coverage). If you simply run pytest these tests will be run. There is a second set of sets that checks whether the package can control basic hardware (e.g. LED blinking, ...). In order to run these tests run `pytest -m physical -s`. Additionally you will need to setup the board as follows
1. Connect an LED with an appropriate resistor to D8 and GND
2. Connect D8 to D2 with a jumper wire
3. Connect D9 (PMW) to A1 with a jumper wire
4. Connect a servo with D10 (PMW) and A0 (XXX and XXX colored wire, put servo into center position)
The third set of tests is marked with `environment_test` and checks that all required packages are installed and a jupyter kernel with CHEM10_Harvard available in it is available.
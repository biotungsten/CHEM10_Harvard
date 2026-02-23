This document contains the documantation for most of the code. In particular it describes the design choices made and how the package was envisioned to be used. The specific behavior of funcitons is documented in the docstrings. 

# Arduino
This section describes how the module communicates with the arduino and gives a brief example of how to setup and interact with an Arduino. 

In communicating we rely on the Telemetrix communication protocol. You can find information on it [here](https://mryslab.github.io/telemetrix/). It installs a sketch on the arduino that monitors the serial connection to wait and process commands send from the *server side* (i.e. the python script). On the python end we find the arduino using the `arduino_cli` utility. Then we compile and install the Telemetrix4Arduino sketch. 

An important thing to understand is the reading system the Telemetrix protocol utilizes. It is based on callbacks, which means that you initially register a pin for reading and then on the *client side* (i.e. the arduino) every loop cycle the value on the pin in question is read and if it differs from the previous value (by a certain amount, which can be specified in the differential parameter; **setting the differential only works the first time, you cannot change the differential amount on subsequent reads**), a callback function is called. In our module we have a callback function that always stores the current value of the voltage on all read pins. This means that the voltage value that a read function returns to you might be old. If that is an issue, you can check this by accesing the second index of the internal read cache, which stores the latest raw timestamp (millis in epoch).

A major issue with this is, that if you have a low differential, and a fluctuating voltage on one of the read pins, your code might get caught up in processing the callbacks, that modify the the read cache. If anyone needs to modify this in the future, I would recommend that you either use a different communication protocol, modify Telemetrix or register and deregister pisns on each read. 

## Example: Connecting an Arduino
You will need to connect the Arduino to a USB port on your computer. Then you can connect the arduino using the following command
```python
board = ArduinoBoard()
board.shutdown()
```
Subsequently you can call the avrious methods available. You will receive an error if you try to create a second instance of `ArduinoBoard`, as you can only connect to a given physical arduino once. If you have multiple arduino boards, you can specify the port address (see code). It is crucial for you to call the shutdown method. We have implemented various safeguards to prevent issues when you don't do it, but it might produce unexpected behavior later on. Once you disconnect the arduino and let it power down, you are safe from these issues, however.

In case you cannot find the instance you already have for a given address, the objects are stored indexed by the address port (which you will get from the error message) in `ArduinoBoard._instances_by_address`.


# Servo
The specific servo motor the functions were optimized for is a Batan Analog S1123, *for which no datasheet exists*. The range of 0 to 20 degrees was very non-linear in tests. Thus we recommend to only use the servo in the angle range of 30 to 180 degrees. In particular one should **never write an angle below 10 degrees**, as this might break the servo. An angle of 65 degrees corresponds to the actual center position (90 degrees) and 180 degrees corresponds to the maximum position (180 degrees). While a mapping based on these values (analog voltage readouts documented in `Servo_behavior.png`, for parameters 340, 2275) is provided, we recommend having the user perform a calibration for reproducibility.

If you modify these parameters in the code the test `TestArduinoFunctions.test_servo_read` in `test_physical.py` will potentially fail. This test checks that the readouts from a servo match the calibration values. As such the test can also be used to troubleshoot calibration issues.

## Example: Scanning over a range of angles

Assuming you have initialized an instance of `ArduinoBoard` you have to initialize a servo, use `servo_write` and then detach the servo as follows

```python
board = ArduinoBoard()
board.initalize_servo(SERVO_PIN)
for i in range(65,180,5):
    board.write_servo(SERVO_PIN, i)
    position_voltage = board.read_analog(SERVO_PIN_READ)
board.detach_servo(SERVO_PIN)
board.shutdown()
```

# Config
The `CB_DIGITAL` and `CB_ANALOG` values deviate from what is in the documentation for Telemetrix but these seem to be correct for firmware version 5.4.4 which is shipped with this package.

# Spectrometer

# Utils

# Testing
We have three sets of tests. The first set of tests checks everything that is purely software side (to the extent that we have testing coverage). If you simply run pytest these tests will be run. There is a second set of sets that checks whether the package can control basic hardware (e.g. LED blinking, ...). In order to run these tests run `pytest -m physical -s`. Additionally you will need to setup the board as follows
1. Connect an LED with an appropriate resistor to D8 and GND
2. Connect D8 to D2 with a jumper wire
4. Connect a servo with D10 (PMW) and A1 (15; orange and white colored wire, put servo into center position)

The third set of tests is marked with `environment` and checks that all required packages are installed and a jupyter kernel with CHEM10_Harvard available in it is available.
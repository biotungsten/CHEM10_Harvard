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


# Servo Motor
The specific servo motor the functions were optimized for is a Batan Analog S1123, *for which no datasheet exists*. The range of 0 to 20 degrees was very non-linear in tests. Thus we recommend to only use the servo in the angle range of 30 to 180 degrees. In particular one should **never write an angle below 10 degrees**, as this might break the servo. An angle of 65 degrees corresponds to the actual center position (90 degrees) and 180 degrees corresponds to the maximum position (180 degrees). While a mapping based on these values (analog voltage readouts documented in `Servo_behavior.png`, for parameters 340, 2275) is provided, we recommend having the user perform a calibration for reproducibility.

The servo readout is only accurate approximately 300 ms after writing a position. See an example (150°, n=3) in `Servo_readout.png`.

If you modify these parameters in the code the test `TestArduinoFunctions.test_servo_read` in `test_physical.py` will potentially fail. This test checks that the readouts from a servo match the calibration values. As such the test can also be used to troubleshoot calibration issues.

## Example: Scanning over a range of angles

Assuming you have initialized an instance of `ArduinoBoard` you have to initialize a servo, use `servo_write` and then detach the servo as follows

```python
board = ArduinoBoard()
board.initialize_servo(SERVO_PIN)
for i in range(65,180,5):
    board.write_servo(SERVO_PIN, i)
    position_voltage = board.read_analog(SERVO_PIN_READ)
board.detach_servo(SERVO_PIN)
board.shutdown()
```

# Config
The `CB_DIGITAL` and `CB_ANALOG` values deviate from what is in the documentation for Telemetrix but these seem to be correct for firmware version 5.4.4 which is shipped with this package.

# Utils

# Environment Testing
We have three sets of tests. The first set of tests checks everything that is purely software side (to the extent that we have testing coverage). If you simply run pytest these tests will be run. There is a second set of sets that checks whether the package can control basic hardware (e.g. LED blinking, ...). In order to run these tests run `pytest -m physical -s`. Additionally you will need to setup the board as follows
1. Connect an LED with an appropriate resistor to D8 and GND
2. Connect D8 to D2 with a jumper wire
4. Connect a servo with D10 (PMW) and A1 (15; orange and white colored wire, put servo into center position)

The third set of tests is marked with `environment` and checks that all required packages are installed and a jupyter kernel with CHEM10_Harvard available in it is available.

# Spectrometer
Before you can use the spectrometer, you will have to connect the board, creating an ArduinoBoard instance.The spectrometer has three major submodules: `Servo`, `Spectrometer`, and `Post`. The `Servo` module provides basic funcitonality to connect to and calibrate the servo motor. It will produce a LUT between the input arm angle and the output voltage reading. The `Specctrometer` module allows for measurement of intensity spectra by calling the servo module to move the arm and taking phototransisotr readings at the relevant arduino pin. Finally, the `Post` module provides several useful postprocessing functions, including cropping and normalizing intensity readings of spectra, and converting from arm angle to wavelength using the blank data. This conversion uses linear interpolation of matched points from dynamic time warping (DTW) between the blank and reference spectra. It is up to you to become familiar with the relevant functions and their parameters in each module, and to track inputs and outputs with your filesystem responsibly.

## Tips
Full documentation of each module can be generated from the docstrings, e.g.

```python
from CHEM10_Harvard.spectrometer import Spectrometer
help(Spectrometer)
# Press `q` to quit the help menu.
```

Always provide full filepathes for where to store output files, and keep your directories neatly organized! Example blank readings and reference data can be found in the `eg` and `ref` folders. Common mistakes, such as a sweep range that cuts off the desired spectrum, and a spectrum taken at too high a resistance resulting in low SNR, are also included. Note that, from a blank spectrum, we are interested in the wavelength range that resembles the LED reference spectrum (see datasheet and example in `ref` folder), not the large peak nearer `angle=150`, which is the central 0-order beam that we will want to crop out using `Post.cropX`.  

## Example: Taking a spectrum
Here we want to connect the board, servo, and make a spectrometer object, using which we can take measurements. Don't forget to replace the relevant filepathes in each function!

```python
from CHEM10_Harvard.arduino import ArduinoBoard
from CHEM10_Harvard.servo import Servo
from CHEM10_Harvard.spectrometer import Spectrometer

board = ArduinoBoard() # connect board
# Connect servo
servo = Servo(pin_servowrite=9, pin_servoread=0, board = board, path_lut="<INSERT>.json")
servo.calibrate()

# Don't forget to turn on the 9V battery!!!

# Initialize spectrometer
spec = Spectrometer(servo, 5)

# Take a spectrum
angles, intensities = spec.measure() # adjust parameters as needed, set `runs=1` to make faster
spec.plot(angles, intensities, path="<INSERT>.png", show_runs = True)
spec.save(angles, intensities, path="<INSERT>.json")
```

You can repeat the steps to take a spectrum as many times as necessary, using your samples of interest. Always take a blank spectrum first, with nothing in the cuvette slot, before conducting your experiment. The blank will be important for postprocessing, specifically calibration between servo arm angle and diffraction grating wavelength.

## Example: Postprocessing
Here we will view our experiment outputs by loading the data into `pandas` dataframes and plotting. We will also use the `Post` module to crop, normalize, and convert the independent variable from arm angle to wavelength.

```python
from CHEM10_Harvard.post import Post
import pandas as pd
import matplotlib.pyplot as plt

post = Post() # instantiate the Post module

# Load data
ref = pd.read_csv('<INSERT>/ref/led_spectrum.csv') # given reference led spectrum .csv
blank = pd.read_json('<INSERT>.json') # your blank spectrum .json

# Take a look at the blank and reference spectra, the curves should have the same shape
blank.plot("angle", "intensity")
plt.show()
ref.plot("wavelength", "intensity")
plt.show()

# Note the independent variable in our data is currently ``angle,'' but we would like
# it to be wavelength. We will use the reference spectrum to calibrate a mapping from 
# spectrometer arm angle to wavelength from the diffraction grating. You are encouraged 
# to read through the `Post` module code to learn more!

blank = post.cropX(blank, "angle", None, 125) # crop out 0-order beam, change upper limit as needed
blank = post.normY(blank, "intensity") # normalize to relative intensities (range 0-1)

# Calibration
post.calibrate(blank, ref, "angle", "relative_intensity") # run DTW

# Convert from arm angle to wavelength
blank = post.addWavelength(blank) # add wavelength column to the blank df
blank # notice the added column for wavelength
blank.plot("wavelength", "intensity") # view results
plt.show()

post.save("<INSERT>.json") # save calibration results dict for future use
```

Note once you have calibrated sucessfully, and the blank spectrum wavelengths look good, you can load your experimental results to dfs and repeat the `addWavelength` function on them to convert the x-axis of any spectrum from arm angle to wavelength. If you wish to use the same calibration in the future, you can save the calibration results to a .json, load the dict at a later time, and add the reloaded calibration dict as a parameter to `addWavelength` instead of recalibrating from the blank and reference data again.

Be aware that `Post.save` only writes `angles`, `wavelengths` and `inverse` — the DTW alignment object and the resampled curves are not JSON serialisable and are dropped. That is enough for `addWavelength`, but when you reload the dict you must convert the two lists back to numpy arrays, because they are passed straight to `np.interp`.

## Going the other way: wavelength to angle
`angle2wavelength` answers "what wavelength is the arm looking at?". Single-wavelength work — kinetics runs in particular, where you park the arm and watch one absorbance decay — needs the opposite question, "where do I move the arm to look at 452 nm?". That is `Post.wavelength2angle`, and `Post.addWavelength`'s counterpart for a scalar target:

```python
arm_angle = float(post.wavelength2angle(452.25))
servo.move(arm_angle)
```

Two properties of this inverse are worth understanding before you trust it.

First, **it clamps rather than extrapolating**, exactly as `angle2wavelength` does. A target outside the calibrated range silently returns the nearest calibrated endpoint. Always check your target is inside `min(calibration["wavelengths"])` to `max(...)` first; the same warning applies to sweeping `Spectrometer.measure` over angles wider than the calibration, which yields a run of duplicate wavelengths at the edges that looks like a real spectral feature.

Second, **DTW maps many angles onto one wavelength**, so the inverse is only defined up to the width of those plateaus. On a typical calibration only about a third of the 300 points carry distinct wavelengths. `wavelength2angle` therefore keeps every calibration point instead of collapsing each plateau to a representative angle, which makes it an exact right inverse — `angle2wavelength(wavelength2angle(w)) == w` to within floating point. Collapsing plateaus first is the obvious implementation and it is wrong: it breaks the round trip by tens of nm at the band edges, because DTW's boundary condition piles a wide span of unmatched wavelengths onto the single first and last angle. If you ever rewrite this, that round-trip identity is the property to test.

Both directions share `Post._calibration_arrays`, which resolves the calibration and coerces it to numpy arrays, so the two cannot drift apart and both behave identically whether they are handed a live calibration or one reloaded from JSON.

## DTW is the only angle/wavelength mechanism
The legacy MATLAB labs calibrated the instrument with Bragg's law: a `w2a.m` helper converted wavelength to diffraction angle through $\lambda = d\sin\theta$, using a hardcoded grating period, anchored on a peak the student read off a plot by hand.

**That approach is deliberately not carried over, and there is no grating-period parameter anywhere in this package.** DTW calibration in `Post.calibrate` replaces it completely. The reasons: it needs no grating constant, no hand-picked peak, and no assumption that the arm pivots exactly on the grating — it matches the measured blank against the manufacturer's reference spectrum and derives the whole mapping from the curve shape. Adding a Bragg-law path back in would give two different answers to the same question, `angle2wavelength` and an `a2w`, which is exactly the redundancy this API avoids.

To validate a calibration, do not reach for a grating period. Check it against itself and against the lamp:

1. **Round trip.** `angle2wavelength(wavelength2angle(w))` must return `w`.
2. **Monotonicity.** The angle → wavelength curve must be smooth and monotonic. A staircase or a curve that doubles back means DTW found a bad alignment, almost always because the 0-order beam was not fully cropped before calibrating.
3. **Known peaks.** The calibrated blank's peaks must land where the LED datasheet says they do. On the example blank in `docs/examples/blank_good.json` the blue die peak comes out at 446 nm and the phosphor hump at 589 nm, spanning 404–720 nm overall — both physically right for a white LED.

Failing (2) or (3) means recalibrate; there is no meaningful way to patch a bad DTW alignment after the fact.

# Testing
Inside `/test` you can find the unit tests for internal dev testing.
Inside `/src/tests` you can find unit tests that are exposed to the users for checking their installation and the hardware they are using.
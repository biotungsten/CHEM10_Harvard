"""
servo.py
06/17/2026
AW, DS, MC
"""




from CHEM10_Harvard.arduino import ArduinoBoard

from pathlib import Path
import json
import time
import matplotlib.pyplot as plt




class Servo:
    """Servo control and calibration -- the motion layer of the spectrometer.

    `Servo` owns arm movement and nothing else. `Spectrometer` composes one of
    these and borrows its `board` for phototransistor reads; `Post` never sees
    it at all, except that `Post.wavelength2angle` produces angles you feed to
    `move`.

    THE LOOKUP TABLE
    `calibrate` walks the arm across a range of commanded angles and records
    the analog feedback voltage the servo reports at each, giving

        self.lut : dict[int, float]   commanded angle (deg) -> ADC counts

    Keys are ints in memory but JSON has no integer keys, so `save` writes them
    as strings and `load` casts them back. `getAngle` inverts the table, which
    answers "where did the arm *actually* go?".

    That question is a diagnostic, not part of the data path. `Spectrometer`
    records the angle it *commanded*, never the angle read back, and so does
    everything downstream of it in `Post`. The LUT's job is to catch a servo
    that is stalling, slipping, or mounted at an offset -- if it comes out
    non-monotonic or flat over part of the range, the spectra taken with that
    arm are not trustworthy, however clean they look.

    BOARD OWNERSHIP
    This class assumes that no other classes are using the same board.
    It will shutdown the board when no Calibration instances are using it.
    Concretely, `_initialized_servo_pins` refcounts users per (board, write
    pin): the first `Servo` on a pin attaches it, `close` detaches it when the
    last user goes away, and shutting down the board's final servo pin shuts
    down the board. So `Spectrometer.close()` -> `Servo.close()` ->
    `board.shutdown()` is the whole teardown chain; you do not call
    `board.shutdown()` yourself when a `Spectrometer` is live.

    PARAMS:
        pin_servowrite : int = servo control pin, usually 9
        pin_servoread : int = servo feedback pin, usually 0
        board : ArduinoBoard = initialized ArduinoBoard object
        path_lut : str = path to save or reload servo output vs. arm angle 
        LUT json file
    NOTE: never command an angle below 10 deg -- it can break the servo. The
        usable range is roughly 30-180 deg; see DOCUMENTATION.md.
    """
    # Track servo pin user counts per board identity. Keyed by id(board). 
    # Then keyed by servo pin number. Value is user count.
    _initialized_servo_pins = {}

    def __init__(
        self,
        pin_servowrite : int,
        pin_servoread : int,
        board : ArduinoBoard,
        path_lut : str = "servo_lut.json",
    ):
        self.board = board # initialized ArduinoBoard object
        self.pin_servowrite = pin_servowrite # usually pin 9
        self.pin_servoread = pin_servoread # usually pin 0
        self.path_lut = Path(path_lut) # lookup table saved json path
        self.lut = {} # lookup table dict
        self._closed = False
        self._board_key = id(self.board)

        self._register_servo()


    def _register_servo(self):
        pins = self.__class__._initialized_servo_pins.setdefault(self._board_key, {})

        pin_users = pins.get(self.pin_servowrite, 0)
        if pin_users == 0:
            self.board.initialize_servo(self.pin_servowrite)
            time.sleep(0.1)
        pins[self.pin_servowrite] = pin_users + 1


    def move(self, theta, delay=0.5):
        """Move servo to angle `theta`
        IN:
            theta = target angle in degrees. Never below 10.
            delay = wait time for servo to settle, in seconds. The feedback
                line only settles ~300 ms after a write, so do not shorten this
                below ~0.3 if you intend to read the position afterwards.
        OUT: None
        """
        self.board.write_servo(self.pin_servowrite, theta)
        time.sleep(delay)


    def readPosition(self, samples=5, delay=0.1):
        """Get reading from servo at current position
        IN:
            samples = number of sample readings to take.
            delay = wait time between samples.

        OUT:
            avg reading from vals, in raw ADC counts (0-1023).
        NOTE: averages several samples because Telemetrix serves analog reads
            from a callback-updated cache, so any single read may be slightly
            stale. The differential is fixed on the first read of a pin and
            cannot be changed afterwards.
        RAISES: RuntimeError if no valid readings arrive -- usually the
            feedback wire is not connected to `pin_servoread`.
        """
        DIFF = 5
        vals = []
        for _ in range(samples):
            v = self.board.analog_read(self.pin_servoread, differential=DIFF)
            if v is not None:
                vals.append(v)
            time.sleep(delay)
        if not vals: raise RuntimeError("No valid feedback readings received.")

        return sum(vals) / len(vals)


    def save(self):
        """Save lookup table to `self.path_lut` as JSON.

        JSON keys are strings, so the int angle keys are written as e.g.
        `{"85": 477.09, "90": 497.91, ...}`. `load` casts them back to int.
        Called automatically at the end of `calibrate`.
        """
        with open(self.path_lut, "w") as f:
            json.dump(self.lut, f, indent=2)


    def load(self):
        """Load lookup table from `self.path_lut`, casting keys back to int.

        This is how later labs reuse a calibration: construct a `Servo` with
        `path_lut` pointing at the file an earlier session wrote, call `load`,
        and skip `calibrate` entirely.
        OUT: self.lut, dict[int, float] of angle (deg) -> ADC counts
        """
        with open(self.path_lut, "r") as f:
            self.lut = json.load(f)
        self.lut = {int(k): v for k, v in self.lut.items()}
        return self.lut


    def calibrate(self, angles=(85, 180), step=5):
        """Calibrate servo over specified angle range, make lookup table

        The first of the instrument's two calibrations. Run it once per
        session, or reuse an earlier one with `load`. Before running, align the
        arm by hand with the centre of the spectrometer.

        Each step commands an angle, waits for the arm to settle, and averages
        several feedback readings, so the run takes roughly
        `(1 + range/step) * 1 s`.
        IN:
            angles : float tuple = (start, stop) angle range in deg, inclusive
                of both ends. The default spans the diffracted spectrum plus
                the 0-order beam.
            step : float = step size increment in deg.
        OUT:
            tbl : dict[int, float], commanded angle (deg) -> mean ADC counts.
                Also stored on `self.lut` and written to `self.path_lut`.
        NOTE: the table should come out monotonic -- counts rising steadily
            with angle, ~290 to ~950 over 30-180 deg on a healthy unit. Plot it
            with `plot()` and check. Flat or reversed stretches mean the arm is
            binding or the feedback wire is loose, and no amount of
            postprocessing will fix spectra taken in that state.
        """
        tbl = {}

        for angle in range(angles[0], angles[1] + 1, step):
            self.move(angle)
            reading = self.readPosition()
            tbl[angle] = reading
            print(f"angle = {angle}, reading = {reading:.2f}")

        self.lut = tbl
        self.save()
        return tbl


    def getAngle(self, reading):
        """Get the predicted angle given the reading and LUT -- the inverse of
        the table `calibrate` builds.

        Diagnostic only. Nothing in `Spectrometer` or `Post` calls this; the
        angle recorded alongside every intensity is the commanded one. Use it
        to verify that the arm reaches the angles it is told to.
        IN:
            reading : float = analog read value in ADC counts, e.g. from
                `readPosition()`
        OUT:
            angle : float = linearly interpolated predicted angle in deg
            error : float = half the difference of closest lut measurements,
                i.e. half a calibration step, and 0.0 when the reading is
                clamped at either end of the table
        NOTE: reloads the LUT from `self.path_lut` on every call, so a table
            assigned in memory but not saved is silently discarded here.
        NOTE: clamps rather than extrapolating -- readings outside the
            calibrated span return the nearest tabulated angle.
        RAISES: RuntimeError if no lookup table could be loaded.
        """
        self.load()
        if not self.lut:
            raise RuntimeError("No lookup table loaded.")

        points = sorted(self.lut.items(), key=lambda x: x[1])

        if reading <= points[0][1]:
            return points[0][0], 0.0
        if reading >= points[-1][1]:
            return points[-1][0], 0.0

        for i in range(len(points) - 1):
            a1, r1 = points[i]
            a2, r2 = points[i + 1]

            if r1 <= reading <= r2:
                if r2 == r1:
                    return a1, 0.0

                t = (reading - r1) / (r2 - r1)
                angle = a1 + t * (a2 - a1)
                error = abs(a2 - a1) / 2
                return angle, error

        raise RuntimeError("Interpolation failed")


    def plot(self):
        """Plots the LUT for insanity check purposes.

        Loads the table from disk if none is in memory. Look for a smooth,
        monotonic angle vs. counts curve; see `calibrate` for what a bad one
        means.
        OUT: None. Always writes to `./servo_lut.png` -- the path is hardcoded
            and ignores `self.path_lut`, so successive calibrations in one
            working directory overwrite each other's plots.
        """
        if not self.lut: self.load()
        if not self.lut: raise RuntimeError("No lookup table found.")

        angles = list(self.lut.keys())
        readings = list(self.lut.values())
        angles, readings = zip(*sorted(zip(angles, readings)))

        plt.figure()
        plt.plot(angles, readings, marker='o')
        plt.xlabel("Angle (deg)")
        plt.ylabel("Analog Reading")
        plt.title("Servo Calibration")
        plt.savefig("servo_lut.png") 


    def close(self):
        """Release this servo's claim on the write pin, and the board with it.

        Decrements the per-(board, pin) user count. The last user of a pin
        detaches the servo; once no servo pins remain on the board, the board
        is shut down. Idempotent, and called for you by `__exit__` and by
        `Spectrometer.close`.
        """
        if self._closed:
            return
        self._closed = True

        # Decrement user count and if this makes pin userless then detach servo. 
        # If this makes board have no servo pins then shutdown board.
        pins = self.__class__._initialized_servo_pins.get(self._board_key)
        if pins is None:
            self.board.shutdown()
            return

        pin_users = pins.get(self.pin_servowrite, 0)
        if pin_users <= 1:
            if self.pin_servowrite in pins:
                self.board.detach_servo(self.pin_servowrite)
                pins.pop(self.pin_servowrite, None)
        else:
            pins[self.pin_servowrite] = pin_users - 1

        if not pins:
            self.__class__._initialized_servo_pins.pop(self._board_key, None)
            self.board.shutdown()


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc, tb):
        self.close()




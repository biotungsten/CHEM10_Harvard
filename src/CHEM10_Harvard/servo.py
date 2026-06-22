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
    """Servo calibration
    This class assumes that no other classes are using the same board. 
    It will shutdown the board when no Calibration instances are using it.
    PARAMS:
        pin_servowrite : int = servo control pin, usually 9
        pin_servoread : int = servo feedback pin, usually 0
        board : ArduinoBoard = initialized ArduinoBoard object
        path_lut : str = path to save or reload servo output vs. arm angle 
        LUT json file
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
            theta = target angle.
            delay = wait time for servo to settle.
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
            avg reading from vals.
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
        """Save lookup table"""
        with open(self.path_lut, "w") as f:
            json.dump(self.lut, f, indent=2)


    def load(self):
        """Load lookup table"""
        with open(self.path_lut, "r") as f:
            self.lut = json.load(f)
        self.lut = {int(k): v for k, v in self.lut.items()}
        return self.lut


    def calibrate(self, angles=(120, 180), step=5):
        """Calibrate servo over specified angle range, make lookup table
        IN:
            angles : float tuple = angle range for calibration in deg.
            step : float = step size increment in deg.
        OUT:
            tbl : lookup table, also saved to file.
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
        """Get the predicted angle given the reading and LUT
        IN:
            reading : float = analog read value
        OUT:
            angle : float = linearly interpolated predicted angle
            error : float = half the difference of closest lut measurements
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
        """Plots the LUT for insanity check purposes"""
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




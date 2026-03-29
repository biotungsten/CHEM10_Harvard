from pathlib import Path
import json
import time
import matplotlib.pyplot as plt
from typing import Union


"""
    Servo calibration.
"""
class Calibration:
    def __init__(
        self,
        pin_servowrite,
        pin_servoread,
        board_class,
        board_address=None,
        path_lut="servo_lut.json",
    ):
        self.board = board_class(address=board_address)
        self.pin_servowrite = pin_servowrite
        self.pin_servoread = pin_servoread
        self.path_lut = Path(path_lut) # lookup table saved json path
        self.lut = {} # lookup table dict

        self.board.initialize_servo(pin_servowrite)
        time.sleep(0.1)


    """
        Move servo to angle `theta`
        IN:
            theta = target angle.
            delay = wait time for servo to settle.
        OUT: None
    """
    def move(self, theta, delay=0.5):
        self.board.write_servo(self.pin_servowrite, theta)
        time.sleep(delay)


    """
        Get reading from servo at current position.
        IN:
            samples = number of sample readings to take.
            delay = wait time between samples.

        OUT:
            avg reading from vals.
    """
    def readPosition(self, samples=5, delay=0.1):
        DIFF = 5
        vals = []
        for _ in range(samples):
            v = self.board.analog_read(self.pin_servoread, differential=DIFF)
            if v is not None:
                vals.append(v)
            time.sleep(delay)
        if not vals: raise RuntimeError("No valid feedback readings received.")

        return sum(vals) / len(vals)


    """
        Save lookup table.
    """
    def save(self):
        with open(self.path_lut, "w") as f:
            json.dump(self.lut, f, indent=2)


    """
        Load lookup table.
    """
    def load(self):
        with open(self.path_lut, "r") as f:
            self.lut = json.load(f)
        self.lut = {int(k): v for k, v in self.lut.items()}
        return self.lut


    """
    Calibrate servo over specified angle range, make lookup table.
    IN:
        angles : float tuple = angle range for calibration in deg.
        step : float = step size increment in deg.
    OUT:
        tbl : lookup table, also saved to file.
    """
    def calibrate(self, angles=(30, 180), step=5):
        tbl = {}

        for angle in range(angles[0], angles[1] + 1, step):
            self.move(angle)
            reading = self.readPosition()
            tbl[angle] = reading
            print(f"angle = {angle}, reading = {reading:.2f}")

        self.lut = tbl
        self.save()
        return tbl


    """
    Get the predicted angle given the reading and LUT.
    IN:
        reading : float = analog read value
    OUT:
        angle : float = linearly interpolated predicted angle
        error : float = half the difference of closest lut measurements
    """
    def getAngle(self, reading):
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


    """
    Plots the LUT for insanity check purposes.
    """
    def plot(self):
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
        self.board.detach_servo(self.pin_servowrite)
        self.board.shutdown()


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc, tb):
        self.close()



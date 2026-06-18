

# from CHEM10_Harvard.arduino import ArduinoBoard
# from CHEM10_Harvard.servo import Servo

import time
import json
import numpy as np
import matplotlib.pyplot as plt
import time


class Spectrometer:
    def __init__(self, servo, pin_photoread):
        self.servo = servo
        self.pin_photoread = pin_photoread
        self.curves = None

    def readPhoto(self, angle, samples=5, delay=0.1):
        DIFF = 5
        vals = []

        self.servo.move(angle)
        for _ in range(samples):
            v = self.servo.board.analog_read(self.pin_photoread, differential=DIFF)
            if v is not None:
                vals.append(v)
            time.sleep(delay)
        if not vals: raise RuntimeError("No valid photo readings received.")

        return sum(vals) / len(vals)

    def sweep(self, angles):
        angles = np.asarray(angles, dtype=int)
        return np.array([self.readPhoto(a) for a in angles], dtype=float)

    def measure(self, angles=np.arange(90, 160, 1), runs=3):
        angles = np.asarray(angles, dtype=int)
        self.curves = np.array([self.sweep(angles) for _ in range(runs)], dtype=float)
        intensities = self.curves.mean(axis=0)
        return angles, intensities

    def plot(self, angles, intensities, path="spectrum.png", show_runs=True):
        if show_runs and self.curves is not None:
            for curve in self.curves:
                plt.plot(angles, curve, alpha=0.35)

        plt.plot(angles, intensities, lw=2, label="average")
        plt.xlabel("Arm angle (deg)")
        plt.ylabel("intensities")
        plt.legend()
        plt.tight_layout()
        plt.savefig(path)
        plt.close()

    def save(self, angles, intensities, path="spectrum.json"):
        with open(path, "w") as f:
            json.dump(
                {
                    "angles": np.asarray(angles, dtype=float).tolist(),
                    "intensities": np.asarray(intensities, dtype=float).tolist(),
                },
                f,
                indent=2,
            )

    def close(self):
        self.servo.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()



import time

from CHEM10_Harvard.arduino import ArduinoBoard
from CHEM10_Harvard.calibration import Calibration

import json
import numpy as np
import matplotlib.pyplot as plt
import time


class Spectrometer:
    def __init__(self, cal, pin_photoread):
        self.cal = cal
        self.pin_photoread = pin_photoread
        self.curves = None

    def readPhoto(self, angle, samples=5, delay=0.1):
        DIFF = 5
        vals = []

        self.cal.move(angle)
        for _ in range(samples):
            v = self.cal.board.analog_read(self.pin_photoread, differential=DIFF)
            if v is not None:
                vals.append(v)
            time.sleep(delay)
        if not vals: raise RuntimeError("No valid photo readings received.")

        return sum(vals) / len(vals)

    def sweep(self, angles):
        angles = np.asarray(angles, dtype=int)
        return np.array([self.readPhoto(a) for a in angles], dtype=float)

    def measure(self, angles=np.arange(120, 180, 5), runs=3):
        angles = np.asarray(angles, dtype=int)
        self.curves = np.array([self.sweep(angles) for _ in range(runs)], dtype=float)
        intensity = self.curves.mean(axis=0)
        return angles, intensity

    def plot(self, angles, intensity, path="spectrum.png", show_runs=True):
        if show_runs and self.curves is not None:
            for curve in self.curves:
                plt.plot(angles, curve, alpha=0.35)

        plt.plot(angles, intensity, lw=2, label="average")
        plt.xlabel("Arm angle (deg)")
        plt.ylabel("Intensity")
        plt.legend()
        plt.tight_layout()
        plt.savefig(path)
        plt.close()

    def save(self, angles, intensity, path="spectrum.json"):
        with open(path, "w") as f:
            json.dump(
                {
                    "angles": np.asarray(angles, dtype=float).tolist(),
                    "intensity": np.asarray(intensity, dtype=float).tolist(),
                },
                f,
                indent=2,
            )

    def close(self):
        self.cal.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


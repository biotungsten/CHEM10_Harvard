from CHEM10_Harvard.arduino import ArduinoBoard
from CHEM10_Harvard.calibration import Calibration

import json
import numpy as np
import matplotlib.pyplot as plt


class Spectrometer:
    def __init__(self, pin_write, pin_read, address=None):
        self.device = Calibration(
            pin_write,
            pin_read,
            ArduinoBoard,
            board_address=address,
        )
        self.curves = None

    def read_at_angle(self, angle):
        self.device.move(angle)
        return float(self.device.readPosition())

    def sweep(self, angles):
        angles = np.asarray(angles, dtype=float)
        return np.array([self.read_at_angle(a) for a in angles], dtype=float)

    def measure(self, angles=np.arange(30, 181, 5), runs=3):
        angles = np.asarray(angles, dtype=float)
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
        self.device.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


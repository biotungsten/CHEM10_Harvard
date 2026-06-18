
"""
    spectrometer.py
    06/17/2026
    AW, DS, MC
"""




# from CHEM10_Harvard.arduino import ArduinoBoard
# from CHEM10_Harvard.servo import Servo

import time
import json
import numpy as np
import matplotlib.pyplot as plt




"""
    Spectrometer functionality.
    Requires calibrated servo object, phototransistor pin #.
    PARAMS:
        servo : Servo = calibrated servo object
        pin_photoread : int = phototransistor reading pin #, usually 5
"""
class Spectrometer:
    def __init__(self, servo, pin_photoread):
        self.servo = servo # calibrated servo object, type servo.Servo
        self.pin_photoread = pin_photoread # usually pin 5
        self.curves = None # stores all readings once measured


    """
        Move servo arm, read photo value.
        IN:
            angle = angle to move servo arm.
            samples = number of photo readings taken for average.
            delay = wait time between servo movements and photo readings (s).
        OUT: average photo reading value.
    """
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


    """
        Sweep servo arm across angles, read photo values.
        IN:
            angles = list of angles to sweep arm.
        OUT: list of photo values corresponding to angles.
    """
    def sweep(self, angles):
        angles = np.asarray(angles, dtype=int)
        return np.array([self.readPhoto(a) for a in angles], dtype=float)


    """
        Measure spectrum by doing `sweep` multiple times and averaging.
        IN:
            angles = list of angles to sweep arm.
            runs = number of runs for avg.
        OUT:
            angles = same list of angles from params.
            intensities = list of averaged photo values corresponding to angles.
    """
    def measure(self, angles=np.arange(90, 160, 1), runs=3):
        angles = np.asarray(angles, dtype=int)
        self.curves = np.array([self.sweep(angles) for _ in range(runs)], dtype=float)
        intensities = self.curves.mean(axis=0)
        return angles, intensities


    """
        Plot spectrum curve, optionally with all runs.
        IN:
            angles = list of angles.
            intensities = list of photo values corresponding to angles.
            path = filepath to save plot.
            show_runs = whether to plot curves of every run or just averaged.
        OUT: None, saves plot.
    """
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


    """
        Save spectrum data to json.
        IN:
            angles = list of angles.
            intensities = list of photo values corresponding to angles.
            path = filepath to save json.
        OUT: None, saves json.
    """
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




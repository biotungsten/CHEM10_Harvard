"""
spectrometer.py
06/17/2026
AW, DS, MC
"""




from CHEM10_Harvard.servo import Servo

import time
import json
import numpy as np
import matplotlib.pyplot as plt




class Spectrometer:
    """Spectrometer functionality
    Requires calibrated servo object, phototransistor pin #
    PARAMS:
        servo : Servo = calibrated servo object
        pin_photoread : int = phototransistor reading pin #, usually 5
    """
    def __init__(self, servo, pin_photoread):
        self.servo : Servo = servo # calibrated servo object, type servo.Servo
        self.pin_photoread : int = pin_photoread # usually pin 5
        self.curves = None # stores all readings once measured


    def readPhoto(self, angle, samples=5, delay=0.1):
        """Move servo arm, read photo value
        IN:
            angle = angle to move servo arm
            samples = number of photo readings taken for average
            delay = wait time between servo movements and photo readings (s)
        OUT: average photo reading value
        """
        DIFF = 5
        vals = []

        self.servo.move(angle)
        for _ in range(samples):
            v = self.servo.board.analog_read(self.pin_photoread, 
                                             differential=DIFF)
            if v is not None:
                vals.append(v)
            time.sleep(delay)
        if not vals: raise RuntimeError("No valid photo readings received.")

        return sum(vals) / len(vals)


    def sweep(self, angles):
        """Sweep servo arm across angles, read photo values
        IN:
            angles = list of angles to sweep arm
        OUT: list of photo values corresponding to angles
        """
        angles = np.asarray(angles, dtype=int)
        return np.array([self.readPhoto(a) for a in angles], dtype=float)


    def measure(self, angles=np.arange(90, 160, 1), runs=3):
        """ Measure spectrum by doing `sweep` multiple times and averaging
        IN:
            angles = list of angles to sweep arm
            runs = number of runs for avg
        OUT:
            angles = same list of angles from params
            intensities = list of averaged photo values corresponding to angles
        """
        angles = np.asarray(angles, dtype=int)
        self.curves = np.array([self.sweep(angles) for _ in range(runs)], dtype=float)
        intensities = self.curves.mean(axis=0)
        return angles, intensities


    def plot(self, angles, intensities, path="spectrum.png", show_runs=True):
        """Plot spectrum curve, optionally with all runs
        IN:
            angles = list of angles
            intensities = list of photo values corresponding to angles
            path = filepath to save plot
            show_runs = whether to plot curves of every run or just averaged
        OUT: None, saves plot
        """
        if show_runs and self.curves is not None:
            for curve in self.curves:
                plt.plot(angles, curve, alpha=0.35)

        plt.plot(angles, intensities, lw=2, label="average")
        plt.xlabel("Arm angle (deg)")
        plt.ylabel("Intensity")
        plt.legend()
        plt.tight_layout()
        plt.savefig(path)
        plt.close()


    def save(self, angles, intensities, path="spectrum.json"):
        """
        Save spectrum data to json
        IN:
            angles = list of angles
            intensities = list of photo values corresponding to angles
            path = filepath to save json
        OUT: None, saves json
        """
        with open(path, "w") as f:
            json.dump(
                {
                    "angle": np.asarray(angles, dtype=float).tolist(),
                    "intensity": np.asarray(intensities, dtype=float).tolist(),
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




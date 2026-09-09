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
import pandas as pd




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
        OUT: average photo reading value and servo measurements as dict
        """
        DIFF = 5
        vals = []

        self.servo.move(angle)
        voltage = self.servo.readPosition(
            samples=samples,
            delay=delay,
        )
        angle_read, angle_error = self.servo.getAngle(voltage)

        for _ in range(samples):
            v = self.servo.board.analog_read(self.pin_photoread, 
                                             differential=DIFF)
            if v is not None:
                vals.append(v)
            time.sleep(delay)
        if not vals: raise RuntimeError("No valid photo readings received.")

        intensity = sum(vals) / len(vals)

        return {
            "voltage": voltage,
            "input_angle": angle,
            "angle": angle_read,
            "angle_error": angle_error,
            "intensity": intensity,
        }


    def sweep(self, angles):
        """Sweep servo arm across angles, read photo values
        IN:
            angles = list of angles to sweep arm
        OUT: dataframe of photo values and servo readings corresponding to angles
        """
        angles = np.asarray(angles, dtype=int)
        out = [
            self.readPhoto(angle)
            for angle in angles
        ]

        return pd.DataFrame(out)


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
        dfs = []

        # Sweeps loop
        for i in range(1, runs + 1):
            inst = self.sweep(angles)
            inst.insert(0, "run", i)
            dfs.append(inst)

        # Combine sweeps into one df
        self.curves = pd.concat(dfs, ignore_index=True)
        self.curves = self.curves.sort_values(by='angle')

        return self.curves


    def plot(self, angles, intensities, path="spectrum.png"):
        """Plot spectrum curve
        IN:
            angles = list of angles
            intensities = list of photo values corresponding to angles
            path = filepath to save plot
        OUT: None, saves plot
        """
        plt.plot(angles, intensities, lw=2, label="average")
        plt.xlabel("Arm angle (deg)")
        plt.ylabel("Intensity")
        plt.legend()
        plt.tight_layout()
        plt.savefig(path)
        plt.close()


    def save(self, path="spectrum.csv"):
        """
        Save spectrum data to csv
        IN:
            angles = list of angles
            intensities = list of photo values corresponding to angles
            path = filepath to save csv
        OUT: None, saves csv
        """
        if self.curves is None:
            raise RuntimeError("No spectrum available, run measure().")
        self.curves.to_csv(path, index=False)


    def close(self):
        self.servo.close()


    def __enter__(self):
        return self


    def __exit__(self, *args):
        self.close()




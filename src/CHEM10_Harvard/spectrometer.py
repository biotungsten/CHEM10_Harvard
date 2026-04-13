from CHEM10_Harvard.arduino import ArduinoBoard
from CHEM10_Harvard.calibration import Calibration

import json
import numpy as np
import matplotlib.pyplot as plt


"""
    Spectrometer calibration and measurement.
"""
class Spectrometer:
    def __init__(self, pin_write, pin_read, address=None):
        self.calib = Calibration(pin_write, pin_read, ArduinoBoard, board_address=address)
        self.curves = []
        self.axis_map = None


    """
        Model for the intensity distribution out the diffraction grating initially. 
    """
    def model(self, x, mode="uniform", f=None):
        if f:
            return np.asarray(f(x), dtype=float)
        if mode == "uniform":
            return np.ones_like(x, dtype=float)
        return np.ones_like(x, dtype=float)


    def sweep(self, angles):
        return np.array([(self.calib.move(a), self.calib.readPosition())[1] for a in angles], dtype=float)


    def run(self, 
            angles=np.arange(30, 181, 5), 
            runs=3, 
            mode="uniform", 
            f=None):
        self.curves = np.array([self.sweep(angles) for _ in range(runs)], dtype=float)
        avg = self.curves.mean(0)
        theory = self.model(np.linspace(0, 1, len(angles)), mode, f)
        return angles, avg, theory


    def buildAngles2WavelengthsMap(self, 
                       angles, 
                       avg, 
                       lambda1, 
                       lambda2, 
                       mode="uniform", 
                       f=None, 
                       path="axis_map.json"):
        y = np.asarray(avg, dtype=float)
        y = y - y.min()
        if y.sum() == 0:
            raise RuntimeError("Calibration curve is flat.")

        x = np.linspace(0, 1, len(angles))
        src = self.model(x, mode, f)
        src = np.asarray(src, dtype=float)

        if src.sum() == 0:
            raise RuntimeError("Source model is flat.")

        cdf_measured = np.cumsum(y)
        cdf_measured /= cdf_measured[-1] # normalize

        cdf_src = np.cumsum(src)
        cdf_src /= cdf_src[-1] # normalize

        x_match = np.interp(cdf_measured, cdf_src, x)
        wavelengths = lambda1 + (lambda2 - lambda1) * x_match

        self.axis_map = {
            "angles": np.asarray(angles, dtype=float).tolist(),
            "wavelengths": wavelengths.tolist(),
            "lambda1": lambda1,
            "lambda2": lambda2,
        }

        with open(path, "w") as f:
            json.dump(self.axis_map, f, indent=2)

        return wavelengths


    def angles2Wavelengths(self, angles, path="axis_map.json"):
        if self.axis_map is None:
            with open(path, "r") as f:
                self.axis_map = json.load(f)
        return np.interp(
            np.asarray(angles, dtype=float),
            np.asarray(self.axis_map["angles"], dtype=float),
            np.asarray(self.axis_map["wavelengths"], dtype=float),
        )


    def plot_calibration(self, 
                         angles, 
                         avg, 
                         theory=None, 
                         wavelengths=None, 
                         path="spectrometer_calibration.png"):
        for c in self.curves:
            plt.plot(angles, c, alpha=0.35)
        
        plt.plot(angles, avg, lw=2, label="avg")
        
        if theory is not None and np.max(theory) != 0:
            plt.plot(angles, theory * np.max(avg) / np.max(theory), "--", label="model")
        
        if wavelengths is not None:
            for a, w in zip(angles, wavelengths):
                plt.text(a, avg.max() * 0.02, f"{w:.0f}", rotation=90, fontsize=7, ha="center")
        
        plt.xlabel("Angle (deg)")
        plt.ylabel("Intensity")
        plt.legend()
        plt.tight_layout()
        plt.savefig(path)
        plt.close()


    def calibrate(self, 
                  lambda1, 
                  lambda2, 
                  angles=np.arange(30, 181, 5), 
                  runs=3, 
                  mode="uniform", 
                  func=None, 
                  path="axis_map.json"):
        angles, avg, theory = self.run(angles=angles, runs=runs, mode=mode, func=func)
        wavelengths = self.buildAngles2WavelengthsMap(angles, avg, lambda1, lambda2, mode=mode, f=func, path=path)
        return angles, avg, wavelengths, theory


    def measure(self, angles=None, runs=3, axis_path="axis_map.json", blank=None, blank_path=None):
        if angles is None:
            if self.axis_map is None:
                with open(axis_path, "r") as f:
                    self.axis_map = json.load(f)
            angles = np.asarray(self.axis_map["angles"], dtype=float)

        self.curves = np.array([self.sweep(angles) for _ in range(runs)], dtype=float)
        intensity = self.curves.mean(0)
        wavelengths = self.angles2Wavelengths(angles, path=axis_path)

        if blank_path is not None:
            with open(blank_path, "r") as f:
                blank = np.asarray(json.load(f)["intensity"], dtype=float)

        if blank is not None:
            blank = np.asarray(blank, dtype=float)
            intensity = intensity / np.where(blank == 0, 1, blank)

        return wavelengths, intensity


    def plot_measurement(self, wavelengths, intensity, path="measurement.png"):
        plt.plot(wavelengths, intensity, lw=2)
        plt.xlabel("Wavelength")
        plt.ylabel("Intensity")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()


    def save_spectrum(self, wavelengths, intensity, path="spectrum.json"):
        with open(path, "w") as f:
            json.dump({
                "wavelengths": np.asarray(wavelengths, dtype=float).tolist(),
                "intensity": np.asarray(intensity, dtype=float).tolist(),
            }, f, indent=2)


    def close(self):
        self.calib.close()


    def __enter__(self):
        return self


    def __exit__(self, *args):
        self.close()


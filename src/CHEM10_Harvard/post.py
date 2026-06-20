
"""
    post.py
    06/17/2026
    AW, DS, MC
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks


class Post:
    def __init__(self):
        self.calibration = None


    """
        Crop a dataframe by x range.
    """
    def cropX(self, df, x_col, xmin=None, xmax=None):
        out = df.copy()
        if xmin is not None: out = out[out[x_col] >= xmin]
        if xmax is not None: out = out[out[x_col] <= xmax]
        return out.reset_index(drop=True)


    """
        Normalize to relative intensities.
    """
    def normY(self, df, y_col, new_col="relative_intensity"):
        out = df.copy()
        out[new_col] = out[y_col] / out[y_col].max()
        return out


    """
        Build angle -> wavelength calibration from automatically detected
        maxima and minima. Blank and ref should already be cropped/normalized.
    """
    def calibrate(
        self,
        blank,
        ref,
        blank_col_angle="angles",
        blank_col_intensity="relative_intensity",
        ref_col_wavelength="wavelength",
        ref_col_intensity="intensity",
        n_features=3,
        prominence=0.05,
        distance=None,
        reverse=True,
        plot=True
    ):
        b = blank.sort_values(blank_col_angle).reset_index(drop=True)
        r = ref.sort_values(ref_col_wavelength).reset_index(drop=True)

        bx = b[blank_col_angle].to_numpy()
        by = b[blank_col_intensity].to_numpy()
        rx = r[ref_col_wavelength].to_numpy()
        ry = r[ref_col_intensity].to_numpy()

        b_max, b_max_props = find_peaks(by, prominence=prominence, distance=distance)
        b_min, b_min_props = find_peaks(-by, prominence=prominence, distance=distance)
        r_max, r_max_props = find_peaks(ry, prominence=prominence, distance=distance)
        r_min, r_min_props = find_peaks(-ry, prominence=prominence, distance=distance)

        b_features = np.concatenate([b_max, b_min])
        r_features = np.concatenate([r_max, r_min])

        b_prom = np.concatenate([b_max_props["prominences"], b_min_props["prominences"]])
        r_prom = np.concatenate([r_max_props["prominences"], r_min_props["prominences"]])

        b_features = b_features[np.argsort(b_prom)[-n_features:]]
        r_features = r_features[np.argsort(r_prom)[-n_features:]]

        b_features = np.sort(b_features)
        r_features = np.sort(r_features)

        if len(b_features) != len(r_features):
            raise ValueError("Could not find matching number of features.")

        degree = min(2, len(b_features) - 1)
        print(f"P{degree} polynomial fit.")

        if degree < 1:
            raise ValueError("Need at least two matched features.")

        angle_points = bx[b_features]

        if reverse:
            wavelength_points = rx[r_features[::-1]]
        else:
            wavelength_points = rx[r_features]

        coeffs = np.polyfit(angle_points, wavelength_points, degree)

        self.calibration = {
            "coeffs": coeffs,
            "degree": degree,
            "angle_points": angle_points,
            "wavelength_points": wavelength_points,
            "blank_features": b.iloc[b_features],
            "ref_features": r.iloc[r_features],
        }

        if plot:
            plt.figure()
            plt.plot(bx, by)
            plt.scatter(bx[b_max], by[b_max], label="maxima")
            plt.scatter(bx[b_min], by[b_min], label="minima")
            plt.scatter(angle_points, by[b_features], marker="x", s=100, label="used")
            plt.xlabel(blank_col_angle)
            plt.ylabel(blank_col_intensity)
            plt.title("Blank detected features")
            plt.legend()
            plt.tight_layout()
            plt.show()

            plt.figure()
            plt.plot(rx, ry)
            plt.scatter(rx[r_max], ry[r_max], label="maxima")
            plt.scatter(rx[r_min], ry[r_min], label="minima")
            plt.scatter(wavelength_points, ry[r_features], marker="x", s=100, label="used")
            plt.xlabel(ref_col_wavelength)
            plt.ylabel(ref_col_intensity)
            plt.title("Reference detected features")
            plt.legend()
            plt.tight_layout()
            plt.show()

        return self.calibration


    """
        Convert arm angles to wavelengths.
    """
    def angle2wavelength(self, angles, calibration=None):
        cal = calibration if calibration is not None else self.calibration
       
        if cal is None:
            raise ValueError("No calibration provided. Run calibrate() first.")
        
        return np.polyval(cal["coeffs"], angles)


    """
        Add wavelength column to experiment dataframes.
    """
    def addWavelengths(
        self,
        df,
        angle_col="angle",
        new_col="wavelength",
        calibration=None
    ):
        out = df.copy()
        out[new_col] = self.angle2wavelength(out[angle_col], calibration)
        return out
    



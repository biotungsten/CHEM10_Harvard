"""
post.py
06/17/2026
AW, DS, MC
"""




import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dtw import dtw
import json




class Post:
    """Post-processing tools for spectrometer, including angle to wavelength 
    mapping
    """
    def __init__(self):
        self.calibration = None


    def cropX(self, df, x_col, xmin=None, xmax=None):
        """Crop a dataframe by specified col
        IN:
            df = input dataframe
            x_col = column name of x values
            xmin = minimum x value to keep (inclusive)
            xmax = maximum x value to keep (inclusive)
        OUT: cropped dataframe
        """
        out = df.copy()
        if xmin is not None: out = out[out[x_col] >= xmin]
        if xmax is not None: out = out[out[x_col] <= xmax]
        return out.reset_index(drop=True)


    def normY(self, df, y_col, new_col="relative_intensity"):
        """Normalize a col of dataframe
        IN:
            df = input dataframe
            y_col = column name of y values to normalize
            new_col = column name to save normalized values in
        OUT: dataframe with new column of normalized values
        """
        out = df.copy()
        out[new_col] = out[y_col] / out[y_col].max()
        return out


    def calibrate(
        self,
        blank,
        ref,
        blank_col_angle="angle",
        blank_col_intensity="relative_intensity",
        ref_col_wavelength="wavelength",
        ref_col_intensity="intensity",
        n=300,
        inverse=True,
        plot=True
    ):
        """Calibrate angle -> wavelength mapping using dynamic time warping (DTW) 
        between blank spectrum and reference spectrum (from LED manufacturer datasheet)
        IN:
            blank = df of blank spectrum
            ref = df of reference spectrum
            blank_col_angle = col name of angle values in blank df
            blank_col_intensity = col name of relative intensity values in blank df
            ref_col_wavelength = col name of wavelength values in ref df
            ref_col_intensity = col name of relative intensity values in ref df
            n = # points to resample for DTW
            inverse = if increasing angles correspond to decreasing wavelengths
            plot = whether to plot calibration procedure
        OUT: calibration dict with keys:
            angles = list of angles
            wavelengths = list of corresponding wavelengths
            alignment = DTW alignment object with matched indices
            blank_resampled = resampled blank spectrum used for DTW
            ref_resampled = resampled reference spectrum used for DTW
            inverse = inverse setting that user inputted
        """
        b = blank.sort_values(blank_col_angle).reset_index(drop=True)
        r = ref.sort_values(ref_col_wavelength).reset_index(drop=True)
        bx = b[blank_col_angle].to_numpy()
        by = b[blank_col_intensity].to_numpy()
        rx = r[ref_col_wavelength].to_numpy()
        ry = r[ref_col_intensity].to_numpy()

        # Normalize intensities and angles/wavelengths to [0, 1] for DTW
        by = by / np.max(by)
        ry = ry / np.max(ry)
        bx_norm = (bx - bx.min()) / (bx.max() - bx.min())
        rx_norm = (rx - rx.min()) / (rx.max() - rx.min())

        # Resample to fixed # of points for DTW
        grid = np.linspace(0, 1, n)
        angles = np.interp(grid, bx_norm, bx)
        blank_y = np.interp(grid, bx_norm, by)
        wavelengths = np.interp(grid, rx_norm, rx)
        ref_y = np.interp(grid, rx_norm, ry)

        if inverse:
            wavelengths = wavelengths[::-1]
            ref_y = ref_y[::-1]

        # Use DTW to align blank and reference spectra
        alignment = dtw(blank_y, ref_y, keep_internals=True)

        # Matched angle and wavelength points from DTW
        angle_points = angles[alignment.index1]
        wavelength_points = wavelengths[alignment.index2]

        # Clean up calibration points (avg duplicates)
        cal = pd.DataFrame({
            "angle": angle_points,
            "wavelength": wavelength_points
        })
        cal = cal.groupby("angle", as_index=False).mean()
        cal = cal.sort_values("angle").reset_index(drop=True)

        # Save calibration results to dict
        self.calibration = {
            "angles": cal["angle"].to_numpy(),
            "wavelengths": cal["wavelength"].to_numpy(),
            "alignment": alignment,
            "blank_resampled": blank_y,
            "ref_resampled": ref_y,
            "inverse": inverse,
        }

        if plot:
            plt.figure()
            plt.plot(grid, blank_y, label="blank")
            plt.plot(grid, ref_y, label="reference")

            step = max(1, len(alignment.index1) // 40)
            for i, j in zip(alignment.index1[::step], alignment.index2[::step]):
                plt.plot(
                    [grid[i], grid[j]],
                    [blank_y[i], ref_y[j]],
                    alpha=0.25
                )

            plt.xlabel("normalized position")
            plt.ylabel("relative intensity")
            plt.title("DTW Mapping")
            plt.legend()
            plt.tight_layout()
            plt.show()

            wl = self.angle2wavelength(angles)

            plt.figure()
            plt.plot(angles, wl)
            plt.xlabel(blank_col_angle)
            plt.ylabel(ref_col_wavelength)
            plt.title("Angle to Wavelength Calibration")
            plt.tight_layout()
            plt.show()

        return self.calibration


    def angle2wavelength(self, angles, calibration=None):
        """Convert arm angles to wavelengths, requires calibration already run
        IN:
            angles = list or array of angles to convert
            calibration = load calibration dict, if None uses self.calibration
        OUT:
            wavelengths = list of mapped wavelengths
        """
        cal = calibration if calibration is not None else self.calibration

        if cal is None:
            raise ValueError("No calibration provided, run calibrate() first.")

        # Linear interpolation of the DTW results
        return np.interp(angles, cal["angles"], cal["wavelengths"])


    def addWavelength(
        self,
        df,
        angle_col="angle",
        new_col="wavelength",
        calibration=None
    ):
        """Add wavelength column to experiment dataframes.
        IN:
            df = input df
            angle_col = col name of angle values in df
            new_col = col name to save wavelength values in df
            calibration = load calibration dict, if None uses self.calibration
        OUT: df with added column of wavelength values
        """
        out = df.copy()
        out[new_col] = self.angle2wavelength(out[angle_col], calibration)
        return out
    

    def save(self, path):
        """Save calibration dict to json file
        IN: path = filepath to save json
        OUT: None, saves json
        """
        if self.calibration is None:
            raise ValueError("No calibration to save.")
        
        with open(path, "w") as f:
            json.dump(
                {
                    "angles": self.calibration["angles"].tolist(),
                    "wavelengths": self.calibration["wavelengths"].tolist(),
                    "inverse": self.calibration["inverse"],
                },
                f,
                indent=2,
            )




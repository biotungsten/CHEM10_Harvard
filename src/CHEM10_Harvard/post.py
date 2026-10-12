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
    mapping.

    `Post` is the only one of the three spectrometer classes that never touches
    hardware: it holds no board, no servo and no pins, and every method is a
    pure pandas/numpy transform. That is deliberate -- it means postprocessing
    can be redone, and a calibration reloaded and reused, long after the
    instrument has been packed away. The single point where results flow back
    towards hardware is `wavelength2angle`, whose output you hand to
    `Servo.move`.

    DATAFRAME CONTRACT
    Every df-taking method copies its input and returns a new df; nothing is
    modified in place. The spectrum dataframes flowing through this class are
    long-form, one row per arm position, and gain columns as they progress:

        angle               deg, commanded arm angle. Written by
                            `Spectrometer.save` / `pd.read_json`.
        intensity           raw ADC counts (0-1023) from the phototransistor.
        relative_intensity  added by `normY`, intensity scaled to peak = 1.
        wavelength          nm, added by `addWavelength`.

    Labs typically add an `absorbance` column of their own; nothing here
    depends on it.

    THE CALIBRATION DICT
    `self.calibration` is set by `calibrate` (or assigned by hand from a
    reloaded JSON) and is consumed by `angle2wavelength`, `wavelength2angle`
    and `addWavelength`. Its keys are documented in full on `calibrate`.
    Methods taking a `calibration=` argument use that dict instead of
    `self.calibration`, so several calibrations can be compared without
    reinstantiating `Post`.

    PARAMS:
        calibration : dict | None = angle -> wavelength mapping, None until
            `calibrate` runs or a saved dict is assigned
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
        OUT: cropped dataframe, same columns and dtypes as `df`, with the row
            index reset to 0..n-1
        NOTE: this is the first step of the calibration lifecycle. A blank must
            have the 0-order beam cropped off before `calibrate` sees it,
            because DTW aligns whole curves: leaving that peak in gives the
            reference spectrum nothing to match it against and produces a
            staircased, non-monotonic angle -> wavelength curve.
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
        OUT: dataframe with one added float column `new_col`, holding
            `y_col` divided by its maximum, so values run 0-1 with peak = 1
        NOTE: the blank is normalised because the reference spectrum from the
            LED datasheet is itself relative (peak = 1) and the two curves must
            be on a common vertical scale before DTW compares them. `calibrate`
            renormalises internally as well, so this step is about being able
            to eyeball the two curves together, not about correctness.
        RAISES: ValueError if the max of `y_col` is ~0 (an all-dark sweep --
            check the 9V battery and the LED).
        """
        if df[y_col].max() < 1e-10:
            raise ValueError("Cannot normalize, max value of y_col is 0.")
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

        This is the second and last calibration of the instrument. The first,
        `Servo.calibrate`, checks that the arm goes where it is told; this one
        gives physical meaning to where it went. It must be run on a blank --
        an empty cuvette slot, so the phototransistor sees the bare LED -- with
        the 0-order beam already cropped off (`cropX`) and the intensities
        normalised (`normY`).
        IN:
            blank = df of blank spectrum, needs the two blank_col_* columns
            ref = df of reference spectrum, needs the two ref_col_* columns;
                ships as `ref/led_spectrum.csv`
            blank_col_angle = col name of angle values in blank df
            blank_col_intensity = col name of relative intensity values in blank df
            ref_col_wavelength = col name of wavelength values in ref df
            ref_col_intensity = col name of relative intensity values in ref df
            n = # points to resample for DTW; both curves are interpolated onto
                a common n-point grid, so n sets the resolution of the mapping
                rather than of the measurement
            inverse = if increasing angles correspond to decreasing wavelengths.
                True for this instrument's geometry, and the default in every lab
            plot = whether to plot calibration procedure (DTW correspondence,
                then the resulting angle -> wavelength curve)
        OUT: calibration dict, also stored on `self.calibration`, with keys:
            angles : ndarray, float, shape (m,), strictly increasing degrees.
                m <= n; it is the number of *distinct* angles DTW matched,
                after duplicate matches are averaged together. m == n in
                practice, since resampling onto a linear grid rarely repeats.
            wavelengths : ndarray, float, shape (m,), nm, aligned elementwise
                with `angles`. Non-increasing when inverse=True. Contains far
                fewer distinct values than m -- roughly a third on a typical
                calibration -- because DTW matches runs of angles onto a single
                wavelength. Those plateaus are expected, not a defect.
            alignment : DTW object from the `dtw` package, `keep_internals=True`.
                `alignment.index1` / `.index2` are the matched index pairs into
                the resampled blank and reference.
            blank_resampled : ndarray, float, shape (n,), blank intensity on the
                common grid, peak-normalised
            ref_resampled : ndarray, float, shape (n,), reference intensity on
                the same grid, reversed if inverse=True
            inverse : bool, the setting that produced this mapping
        NOTE: only `angles`, `wavelengths` and `inverse` survive `save` -- see
            that method. The other three keys are diagnostics for the plots.
        NOTE: validate the result before trusting it. The angle -> wavelength
            curve must be smooth and monotonic; the calibrated blank's peaks
            must land where the LED datasheet says (blue die ~446 nm, phosphor
            hump ~589 nm, span ~404-720 nm on the shipped example); and
            `angle2wavelength(wavelength2angle(w))` must return `w`. A bad DTW
            alignment cannot be patched afterwards -- crop harder and recalibrate.
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

            plt.xlabel("Normalized position")
            plt.ylabel("Relative intensity")
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


    def _calibration_arrays(self, calibration=None):
        """Resolve a calibration to (angles, wavelengths) numpy arrays.

        Shared by `angle2wavelength` and `wavelength2angle` so the two
        directions cannot drift apart. Converting explicitly matters because
        `save`/`json` round trips the arrays to plain lists.
        """
        cal = calibration if calibration is not None else self.calibration

        if cal is None:
            raise ValueError("No calibration provided, run calibrate() first.")

        return (np.asarray(cal["angles"], dtype=float),
                np.asarray(cal["wavelengths"], dtype=float))


    def angle2wavelength(self, angles, calibration=None):
        """Convert arm angles to wavelengths, requires calibration already run
        IN:
            angles = list or array of angles to convert
            calibration = load calibration dict, if None uses self.calibration
        OUT:
            wavelengths = list of mapped wavelengths
        NOTE: clamps rather than extrapolating, so angles outside the calibrated
            range come back as the nearest calibrated endpoint. Sweeping wider
            than you calibrated therefore yields a run of duplicate wavelengths
            at the edges, which looks like a real spectral feature but is not.
        """
        ang, wl = self._calibration_arrays(calibration)

        # Linear interpolation of the DTW results
        return np.interp(angles, ang, wl)


    def wavelength2angle(self, wavelengths, calibration=None):
        """Convert wavelengths to arm angles; the inverse of `angle2wavelength`.

        Needed whenever you want to park the arm at a *chosen* wavelength rather
        than read the wavelength of wherever the arm happens to be -- for
        example, single-wavelength kinetics runs.
        IN:
            wavelengths = list or array of wavelengths to convert
            calibration = load calibration dict, if None uses self.calibration
        OUT:
            angles = list of mapped arm angles in degrees
        NOTE: clamps rather than extrapolating, exactly as `angle2wavelength`
            does. Check your target is inside the calibrated wavelength range
            before relying on the result.
        NOTE: DTW maps many angles onto one wavelength, so the inverse is only
            defined up to the width of those plateaus. We keep every calibration
            point rather than collapsing the plateaus, which makes this an exact
            right inverse: angle2wavelength(wavelength2angle(w)) == w to within
            floating point. Collapsing plateaus to a representative angle
            instead breaks the round trip badly (tens of nm) at the band edges,
            where DTW's boundary condition piles a wide wavelength span onto a
            single angle.
        """
        ang, wl = self._calibration_arrays(calibration)

        # np.interp needs its x non-decreasing. `calibrate` sorts by angle, and
        # with inverse=True wavelength then runs downwards, so flip both.
        if wl.size > 1 and wl[0] > wl[-1]:
            wl, ang = wl[::-1], ang[::-1]

        return np.interp(wavelengths, wl, ang)


    def addWavelength(
        self,
        df,
        angle_col="angle",
        new_col="wavelength",
        calibration=None
    ):
        """Add wavelength column to experiment dataframes.

        This is the routine workhorse: run it once on the blank to check the
        calibration, then on every sample df to put its x-axis in nm. Sample
        spectra are calibrated with the blank's calibration, never with one of
        their own -- an absorbing sample is the wrong shape to align against
        the LED reference.
        IN:
            df = input df
            angle_col = col name of angle values in df
            new_col = col name to save wavelength values in df
            calibration = load calibration dict, if None uses self.calibration
        OUT: copy of `df` with one added float column `new_col` in nm; row
            order and every existing column are untouched
        NOTE: inherits the clamping of `angle2wavelength`. Angles outside the
            calibrated range come back as the nearest calibrated endpoint, so
            keep `Spectrometer.measure` inside `calibration["angles"]`.
        """
        out = df.copy()
        out[new_col] = self.angle2wavelength(out[angle_col], calibration)
        return out
    

    def save(self, path):
        """Save calibration dict to json file

        Writes only the three keys needed to reuse the mapping -- `angles`,
        `wavelengths` and `inverse` -- as plain JSON lists. `alignment`,
        `blank_resampled` and `ref_resampled` are dropped: the DTW object is
        not JSON serialisable and the resampled curves are diagnostics that the
        conversion methods never read.

        To reload, parse the JSON and put the two lists back into numpy arrays
        before assigning to `self.calibration`, because they are handed
        straight to `np.interp`:

            with open(path) as f:
                cal = json.load(f)
            cal["angles"] = np.asarray(cal["angles"], dtype=float)
            cal["wavelengths"] = np.asarray(cal["wavelengths"], dtype=float)
            post.calibration = cal

        IN: path = filepath to save json
        OUT: None, saves json
        RAISES: ValueError if there is no calibration to save.
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




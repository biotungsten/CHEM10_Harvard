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
        NOTE: DTW matches curve *shapes*, so it is thrown off when the blank's
            peak heights differ from the datasheet's (weak battery, detector
            response, alignment). `calibratePeaks` uses only peak positions and
            is the more robust choice in that case.
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


    @staticmethod
    def _refineExtremum(x, y, i, half_window):
        """Sub-sample position of the extremum at index i: least-squares
        parabola through the points within `half_window` of `y[i]` (contiguous
        around i, at least 3), returning its vertex. Falls back to x[i] when
        the fit is degenerate or its vertex leaves the window.
        """
        lo = hi = i
        while lo > 0 and abs(y[lo - 1] - y[i]) <= half_window: lo -= 1
        while hi < len(y) - 1 and abs(y[hi + 1] - y[i]) <= half_window: hi += 1
        lo, hi = max(0, min(lo, i - 1)), min(len(y) - 1, max(hi, i + 1))
        if hi - lo < 2:
            return float(x[i])

        a, b, _ = np.polyfit(x[lo:hi + 1], y[lo:hi + 1], 2)
        if a == 0:
            return float(x[i])
        vertex = -b / (2 * a)
        return float(vertex) if x[lo] <= vertex <= x[hi] else float(x[i])


    def _findFeatures(self, x, y):
        """Locate the two main peaks and the valley between them.
        IN:
            x = ndarray, strictly increasing positions (angles or wavelengths)
            y = ndarray, intensities aligned with x
        OUT: ndarray of 3 floats, ascending x: [first peak, valley, second peak]
        NOTE: peaks are the two most *prominent* interior local maxima of a
            3-point smoothed copy of y, so absolute heights never matter, only
            how far each peak stands out from its surroundings. Edge points are
            never peaks, but an uncropped 0-order beam will still win.
        RAISES: ValueError if fewer than two interior maxima exist.
        """
        y = y - y.min()
        ys = np.convolve(np.pad(y, 1, mode="edge"), np.ones(3) / 3, "valid")

        maxima = [i for i in range(1, len(ys) - 1)
                  if ys[i] > ys[i - 1] and ys[i] >= ys[i + 1]]
        if len(maxima) < 2:
            raise ValueError("Need two peaks to calibrate, found "
                             f"{len(maxima)}. Check the crop and the LED.")

        # Prominence: height above the higher of the two lowest points
        # reached before meeting a taller peak (or the edge) on either side
        def prominence(i):
            left = ys[:i + 1]
            taller = np.nonzero(left > ys[i])[0]
            lmin = left[taller[-1]:].min() if taller.size else left.min()
            right = ys[i:]
            taller = np.nonzero(right > ys[i])[0]
            rmin = right[:taller[0] + 1].min() if taller.size else right.min()
            return ys[i] - max(lmin, rmin)

        prom = {i: prominence(i) for i in maxima}
        p1, p2 = sorted(sorted(maxima, key=prom.get)[-2:])
        v = p1 + int(np.argmin(ys[p1:p2 + 1]))

        def refine(i, depth, find_max):
            # Snap to the raw extremum near the smoothed one, then fit
            nb = slice(max(0, i - 2), min(len(y), i + 3))
            j = nb.start + int(np.argmax(y[nb]) if find_max else np.argmin(y[nb]))
            return self._refineExtremum(x, y, j, 0.25 * depth)

        depth_v = min(ys[p1], ys[p2]) - ys[v]
        return np.array([refine(p1, prom[p1], True),
                         refine(v, depth_v, False),
                         refine(p2, prom[p2], True)])


    def calibratePeaks(
        self,
        blank,
        ref,
        blank_col_angle="angle",
        blank_col_intensity="intensity",
        ref_col_wavelength="wavelength",
        ref_col_intensity="intensity",
        inverse=True,
        n=300,
        plot=True
    ):
        """Calibrate angle -> wavelength mapping with a straight line through
        matched spectral features (blue die peak, valley, phosphor peak)

        An alternative to `calibrate` that uses only *where* the features are,
        never how tall they are. The white LED has two peaks (blue die ~445 nm,
        phosphor hump ~590 nm) with a valley between; those three positions
        are found in the blank (in degrees) and in the reference (in nm),
        paired up, and a least-squares line wavelength = slope*angle +
        intercept is fit through them. Because the dark offset is subtracted
        and only positions are used, a blank whose blue peak is twice the
        phosphor's -- or half -- calibrates exactly the same.
        IN:
            blank = df of blank spectrum with the 0-order beam cropped off
                (`cropX`); normalisation is optional, raw counts work
            ref = df of reference spectrum, ships as `ref/led_spectrum.csv`
            blank_col_angle = col name of angle values in blank df
            blank_col_intensity = col name of intensity values in blank df
            ref_col_wavelength = col name of wavelength values in ref df
            ref_col_intensity = col name of intensity values in ref df
            inverse = if increasing angles correspond to decreasing wavelengths.
                True for this instrument's geometry
            n = # points on which the line is tabulated for `self.calibration`
            plot = whether to plot detected features and the fitted line
        OUT: calibration dict, also stored on `self.calibration`, with the same
            `angles`, `wavelengths` and `inverse` keys as `calibrate` (so every
            conversion method and `save` work unchanged), plus:
            slope : float, nm/deg
            intercept : float, nm
            features : list of (name, angle, wavelength) tuples, the matched
                pairs the line was fit through
            residuals : ndarray, nm, fitted minus reference wavelength per
                feature. More than a few nm means a feature was misdetected.
            method : "peaks"
        NOTE: `angles` spans the blank's angle range only, and conversions
            clamp outside it, exactly as for a DTW calibration.
        RAISES: ValueError if either curve lacks two peaks, or if the fitted
            slope's sign contradicts `inverse`.
        """
        b = blank.sort_values(blank_col_angle).reset_index(drop=True)
        r = ref.sort_values(ref_col_wavelength).reset_index(drop=True)
        bx = b[blank_col_angle].to_numpy(dtype=float)
        by = b[blank_col_intensity].to_numpy(dtype=float)
        rx = r[ref_col_wavelength].to_numpy(dtype=float)
        ry = r[ref_col_intensity].to_numpy(dtype=float)

        blank_feat = self._findFeatures(bx, by)
        ref_feat = self._findFeatures(rx, ry)
        names = ["blue", "valley", "phosphor"]  # ascending wavelength
        if inverse:
            ref_feat, names = ref_feat[::-1], names[::-1]

        slope, intercept = np.polyfit(blank_feat, ref_feat, 1)
        if (slope < 0) != inverse:
            raise ValueError(
                f"Fitted slope {slope:.2f} nm/deg contradicts inverse={inverse}; "
                "features were probably misdetected.")

        angles = np.linspace(bx.min(), bx.max(), n)
        self.calibration = {
            "angles": angles,
            "wavelengths": slope * angles + intercept,
            "inverse": inverse,
            "slope": float(slope),
            "intercept": float(intercept),
            "features": [(nm, float(a), float(w))
                         for nm, a, w in zip(names, blank_feat, ref_feat)],
            "residuals": slope * blank_feat + intercept - ref_feat,
            "method": "peaks",
        }

        if plot:
            fig, axs = plt.subplots(1, 2, figsize=(12, 4))
            axs[0].plot(bx, by)
            axs[1].plot(rx, ry, color="tab:orange")
            for ax, xs, fx, fy in ((axs[0], bx, blank_feat, by),
                                   (axs[1], rx, ref_feat, ry)):
                for f, nm in zip(fx, names):
                    ax.axvline(f, ls="--", alpha=0.5, color="k")
                    ax.annotate(nm, (f, np.interp(f, xs, fy)))
            axs[0].set_xlabel(blank_col_angle)
            axs[0].set_title("Blank features")
            axs[1].set_xlabel(ref_col_wavelength)
            axs[1].set_title("Reference features")
            plt.tight_layout()
            plt.show()

            plt.figure()
            plt.plot(angles, self.calibration["wavelengths"], label="fit")
            plt.scatter(blank_feat, ref_feat, color="k", zorder=3,
                        label="features")
            plt.xlabel(blank_col_angle)
            plt.ylabel(ref_col_wavelength)
            plt.title(f"Peak calibration: {slope:.2f} nm/deg")
            plt.legend()
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




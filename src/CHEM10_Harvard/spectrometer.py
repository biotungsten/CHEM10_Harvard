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
    """Spectrometer functionality -- the acquisition layer.

    Requires calibrated servo object, phototransistor pin #

    HOW IT RELATES TO THE OTHER TWO CLASSES
    A `Spectrometer` composes a `Servo` and reaches through it for the board
    (`self.servo.board`) rather than holding one itself, so there is a single
    owner of the connection and a single teardown path: `Spectrometer.close()`
    -> `Servo.close()` -> `board.shutdown()`. Its output -- angles and
    intensities -- is what `Post` consumes; it never imports `Post` or knows
    anything about wavelengths.

    THE ANGLE AXIS IS THE COMMANDED ANGLE
    Every reading is filed under the angle that was *written* to the servo, not
    the angle read back from its feedback line. The servo LUT is not consulted
    here at all. This is what makes a spectrum reproducible across sessions --
    two sweeps over `np.arange(90, 161)` share an x-axis exactly, so a sample
    can be divided by a blank pointwise -- but it also means a mechanically
    misbehaving arm produces a clean-looking spectrum with the wrong x-axis.
    `Servo.calibrate` / `Servo.plot` are how you rule that out.

    PARAMS:
        servo : Servo = calibrated servo object
        pin_photoread : int = phototransistor reading pin #, usually 5
        curves : ndarray | None = every individual sweep from the last
            `measure` call, shape (runs, n_angles), None until then. `measure`
            returns only the mean, so this is where per-run scatter lives --
            use it for error bars rather than re-measuring.
    NOTE: the phototransistor read shares the board with the servo feedback
        read, so both go through the same Telemetrix callback cache. Both
        average several samples for that reason.
    """
    def __init__(self, servo, pin_photoread):
        self.servo : Servo = servo # calibrated servo object, type servo.Servo
        self.pin_photoread : int = pin_photoread # usually pin 5
        self.curves = None # stores all readings once measured


    def readPhoto(self, angle, samples=5, delay=0.1):
        """Move servo arm, read photo value
        IN:
            angle = angle to move servo arm, in degrees
            samples = number of photo readings taken for average
            delay = wait time between servo movements and photo readings (s)
        OUT: average photo reading value, raw ADC counts (0-1023)
        NOTE: always moves the servo first, which costs the servo's settle
            delay (~0.5 s) even if the arm is already there. For fixed-angle
            work such as kinetics, park the arm once with `servo.move` and then
            read `board.analog_read(pin_photoread)` directly in your own loop.
        RAISES: RuntimeError if no valid readings arrive.
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
        """Sweep servo arm across angles, read photo values -- one pass
        IN:
            angles = list of angles to sweep arm, in degrees. Cast to int, so
                fractional angles are truncated; the arm is stepped in the
                order given.
        OUT: ndarray of float photo values, shape (len(angles),), aligned
            elementwise with `angles`
        """
        angles = np.asarray(angles, dtype=int)
        return np.array([self.readPhoto(a) for a in angles], dtype=float)


    def measure(self, angles=np.arange(90, 160, 1), runs=3):
        """ Measure spectrum by doing `sweep` multiple times and averaging
        IN:
            angles = list of angles to sweep arm, in degrees, cast to int. Keep
                this inside the range you calibrated: `Post.angle2wavelength`
                clamps rather than extrapolating, so sweeping wider produces a
                run of duplicate wavelengths at the edges that looks like a real
                spectral feature.
            runs = number of runs for avg. Use the same `angles` for the blank
                and every sample so their intensities can be divided pointwise.
        OUT:
            angles = ndarray of int, the same angles from params
            intensities = ndarray of float, shape (len(angles),), mean ADC
                counts across runs
        SIDE EFFECT: stores all `runs` individual sweeps on `self.curves`,
            shape (runs, len(angles)), overwriting any previous measurement.
            Read it before the next `measure` call if you need per-run spread.
        NOTE: a full sweep costs roughly `len(angles) * 1 s` per run, so the
            default is a few minutes. Drop to `runs=1` while debugging.
        """
        angles = np.asarray(angles, dtype=int)
        self.curves = np.array([self.sweep(angles) for _ in range(runs)], dtype=float)
        intensities = self.curves.mean(axis=0)
        return angles, intensities


    def plot(self, angles, intensities, path="spectrum.png", show_runs=True):
        """Plot spectrum curve, optionally with all runs
        IN:
            angles = list of angles, in degrees
            intensities = list of photo values corresponding to angles
            path = filepath to save plot
            show_runs = whether to plot curves of every run (from
                `self.curves`) faintly behind the average. Runs that visibly
                separate mean the arm or the light source drifted during the
                measurement.
        OUT: None, saves plot to `path` and closes the figure
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

        Writes two equal-length float arrays as `{"angle": [...],
        "intensity": [...]}`, which is exactly the column-oriented layout
        `pd.read_json` turns into the two-column spectrum dataframe that `Post`
        expects:

            blank = pd.read_json(path)     # columns: angle, intensity

        Only the averaged curve is written. `self.curves` is not saved -- if
        you need the per-run spread later, save it yourself.
        IN:
            angles = list of angles, in degrees
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
        """Shut down the instrument by closing the servo, which releases the
        pin and, once no servo pins remain, the board itself. Also invoked by
        `__exit__`.
        """
        self.servo.close()


    def __enter__(self):
        return self


    def __exit__(self, *args):
        self.close()




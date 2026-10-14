from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from CHEM10_Harvard.post import Post

REF = pd.read_csv(Path(__file__).parents[1] / "ref" / "led_spectrum.csv")
SLOPE, INTERCEPT = -11.5, 1580.0  # nm/deg, nm


def synthetic_blank(blue_gain=1.8, offset=165.0, noise=2.0, seed=0):
    """Blank as the instrument would see the reference through a known
    linear angle -> wavelength map, with distorted peak heights."""
    angles = np.arange(70, 106, dtype=float)
    wl = SLOPE * angles + INTERCEPT
    y = np.interp(wl, REF["wavelength"], REF["intensity"], left=0, right=0)
    y = y * (1 + (blue_gain - 1) * np.exp(-((wl - 445) / 25) ** 2)) * 400
    y += offset + np.random.default_rng(seed).normal(0, noise, angles.size)
    return pd.DataFrame({"angle": angles, "intensity": y})


@pytest.mark.parametrize("blue_gain", [0.5, 1.0, 1.8])
def test_calibratePeaks_recovers_line(blue_gain):
    post = Post()
    cal = post.calibratePeaks(synthetic_blank(blue_gain), REF, plot=False)

    assert {"angles", "wavelengths", "inverse"} <= cal.keys()
    assert cal["method"] == "peaks"
    assert cal["slope"] == pytest.approx(SLOPE, rel=0.05)
    assert np.abs(cal["residuals"]).max() < 5

    # mapped wavelengths agree with the true line across the sweep
    angles = np.arange(70, 106)
    assert np.abs(post.angle2wavelength(angles) - (SLOPE * angles + INTERCEPT)).max() < 8

    probe = np.linspace(cal["wavelengths"].min(), cal["wavelengths"].max(), 25)
    assert np.allclose(post.angle2wavelength(post.wavelength2angle(probe)), probe)


def test_calibratePeaks_feature_order():
    cal = Post().calibratePeaks(synthetic_blank(), REF, plot=False)
    names = [f[0] for f in cal["features"]]
    assert names == ["phosphor", "valley", "blue"]  # ascending angle, inverse=True
    wl = {f[0]: f[2] for f in cal["features"]}
    assert wl["blue"] == pytest.approx(445, abs=5)
    assert wl["phosphor"] == pytest.approx(588, abs=8)


def test_calibratePeaks_single_peak_raises():
    x = np.arange(0, 50, dtype=float)
    blank = pd.DataFrame({"angle": x, "intensity": np.exp(-((x - 25) / 5) ** 2)})
    with pytest.raises(ValueError):
        Post().calibratePeaks(blank, REF, plot=False)

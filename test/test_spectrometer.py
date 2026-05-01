
from CHEM10_Harvard.spectrometer import Spectrometer

with Spectrometer(9, 0) as spec:
    angles, avg, wavelengths, theory = spec.calibrate(400, 700, runs=5)
    spec.plot_calibration(angles, avg, theory, wavelengths)
    spec.save_spectrum(wavelengths, avg, "blank.json")

with Spectrometer(9, 0) as spec:
    wavelengths, intensity = spec.measure(runs=5, blank_path="blank.json")
    spec.plot_measurement(wavelengths, intensity)
    spec.save_spectrum(wavelengths, intensity, "sample.json")


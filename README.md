# CHEM10_Harvard

<a href="https://github.com/conda-forge/chem10-harvard-feedstock/actions/workflows/conda-build.yml">
    <img src="https://github.com/conda-forge/chem10-harvard-feedstock/actions/workflows/conda-build.yml/badge.svg?event=push&branch=main">
</a>

This is a package to interface with the spectrometer built in CHEM 10 at Harvard College. You can learn more about CHEM 10 [here](https://www.chemistry.harvard.edu/undergraduate-programs/exploration).

Documentation for the spectrometer, including the LED used and calibration data, as well as for the code is provided in `/docs`. If you are a student at Harvard College, more detailed instructions can be found in `STUDENT.md`.

# Installation
This package is available on PyPi and conda-forge. Installation is possible via many common package managers as shown below
```bash
pip install chem10-harvard
conda install -c conda-forge chem10-harvard
pixi add chem10-harvard
```

There are additional requirements, that cannot be installed via conda and/or pip.
1) **telemetrix** (>=1.46): `pip install chem10-harvard[hardware]` or as a seperate install via `pip install telemetrix=1.46`
2) **arduino-cli** (>=1.4.0): via brew `brew install arduino-cli` or as a [direct installation](https://arduino.github.io/arduino-cli/1.3/installation/)

To verify that these additional requirements are fulfilled you can run `python -m pytest -m environment` (requires `pytest, pytest-cov`).
# CHEM10_Harvard

# Installation
 First you have to have installed Python 3.13 or higher ([here](https://docs.python.org/3.13/using/windows.html) are instructions on how to install Python on Windows). Python is pre-installed on macOS and linux. We recommend you setup a virtual envrionment ([venv](https://docs.python.org/3/library/venv.html)) where you use the library. Before activating the virtual environment take care to deactivate all other environments (e.g. other venvs or conda environments). You are also free to use packaging managers (e.g. [uv](https://docs.astral.sh/uv/guides/install-python/), [conda](https://docs.conda.io/en/latest/), ...). This might be advantageous if you plan to work in STEM fields where `conda` is commonly used.

You also need to install arduino-cli. Instructions on its installation can be found [here](https://arduino.github.io/arduino-cli/1.3/installation/). Unless you have already installed the package manager `brew` we recommend that you use the installation script as explained on the linked page.

In the course you will use jupyter notebooks to execute code. In order to be able to use your virtual environment you will need to execute the following line of code (if you want to you can change the name of the kernel by replacing `CHEM10_environment` by your name)
```bash
python -m ipykernel install --user --name=CHEM10_environment
```

In order to check that all dependencies are present for the package to work you can install `pytest` and run 
```bash
python -m pytest -m environment_test
```

If you see a green line at the end that says `N passed in N.NNs` you are ready to proceed. 
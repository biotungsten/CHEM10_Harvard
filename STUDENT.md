# CHEM10_Harvard

These are instructions on how to install all software necessary to run the code contained in this package, to interface with the spectrometer built in CHEM 10 at Harvard College. If you are familiar with Python already, these instructions might be too specific and you might want to look at the more general `README.md` instructions.

Most of the work you are doing in this class will happen in the form of jupyter notebooks. You can edit and run them either in your browser or in a dedicated IDE such as [VSCode](https://code.visualstudio.com). The latter will be especially useful if you plan on doing other development work. 

Before starting with anything you will need to have `python` available on your system. If you are using macOS or linux, it is preinstalled in your operating system. If you use Windows you can find installation instructions [here](https://docs.python.org/3.13/using/windows.html). If you are a Windows user it is also highly recommended that you install [git for windows](https://gitforwindows.org) and use the shell provided there instead of PowerShell. Once you have installed python open a terminal (PowerShell on Windows) and run `python --version`. You should see that you have a version of `3.12.0` or higher. If not you will need to update your python version or install a second version of python.

Working with python you will have to deal with many packages. These packages allow you to resue code written by others previously. As packages also use packages (called a packages *dependencies*) it becomes crucial to keep track to which packages python has access, especially when some packages require certain versions of other packages. There is various so called package managers that allow you to keep track of the packages that you are using. You can choose whichever package manager you want to use but we will describe how to use the built-in package manager `pip` and the commonly used `conda`. Other popular options include `uv`, `pixi` and `mamba` (a conda derivative).

Package managers generally create what is called an environment. This is a layer of abstraction that isolates the python executable that you are using and the packages installed. It ensures that e.g. if you have a different version of a package installed in a different environment, you use the correct version.

## Pip + venv
First we want to create a virtual environemnet using the built-in `venv` tool. In the directory in which you want to install your environment you can run
```bash
python -m venv /path/to/new/virtual/environment
```
To use your environment you need to make sure that it is active. Before you use it run
```bash
source /path/to/new/virtual/environment/bin/activate
```
If you are ever unsure which environment you are using, you can check the path corresponding to your python executable `which python`. If this is the path you specified for your environment when you created it you are in the correct environment. 

We can now install the CHEM10_Harvard package by running
```bash
pip install chem10-harvard telemetrix
```

## Conda
If you want to use `conda` instead of `pip` you will first need to install `conda`. You can find instructions [here](https://www.anaconda.com/docs/getting-started/installation). There you choose your OS. Then you can choose between Anaconda and miniconda. The former has more functionalities, is, however, also larger in size. 

Once installed you need to create a conda environment and activate it
```bash
conda create -n name_of_environment
conda activate name_of_environment
```

Then you install the package into the environment
```bash
conda install -c conda-forge chem10-harvard 
```

Not all packages exist on conda. One dependency of this package is called `telemetrix` (details [here](https://mryslab.github.io/telemetrix/)) and we have to install it via `pip`. Thus you will need to run
```bash
python -m pip install telemetrix
```
It is important to always first install your dependencies available on conda and to only then install pip dependencies, otherwise you will encounter problems within the realm of dependenecy hell (https://en.wikipedia.org/wiki/Dependency_hell).

As a quick check of your installation you can run 
```bash
python -c "import CHEM10_Harvard"
```

## Installing the arduino-cli
One additional piece of software needed is `arduino-cli`. It allows us to interface with the Arduino microcontroller and obtain information about the microcontroller programatically. There are package managers allowing you to install software beyond python packages, such as [`brew`](https://brew.sh). You can install `arduino-cli` using brew. Otherwise you can install it using the following command 
```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
```
More details on the installation are given in the [documentation](https://docs.arduino.cc/arduino-cli/installation/).

## Setting up a jupyter kernel
In order for Jupyter to know which python to use and how to interact with it, you need to create something called a kernel. To do so in your environment run
```bash
python -m ipykernel install --user --name=CHEM10_environment
```
(you can choose an arbitrary name). Then when opening a Jupyter notebook `CHEM10_environment` should be an option in the list where you can choose your kernel.

## Verifying your environment
In order to check that you installed everything correctly you should install the packages `pytest` and `pytest-cov` (you are familiar with installing packages at this point; they are installed the same way that the CHEM10_Harvard package is installed). These provide utilities for testing software

In order to check that all dependencies are present for the package to work you can install `pytest` and run 
```bash
python -m pytest --pyargs CHEM10_Harvard -m environment
```
(`--pyargs CHEM10_Harvard` tells pytest to find these tests inside your installed copy of the package, so this works no matter which directory you run it from.)

If you see a green line at the end that says `N passed in N.NNs` you are ready to proceed. 

## Verifying your hardware setup
Once you have installed the `hardware` extra (`pip install "CHEM10_Harvard[hardware]"`, or by installing `telemtrix` manually) and built the physical circuit for testing described in `docs/DOCUMENTATION.md`. Additionally you need to install the `pytest` and `pytest-cov` packages with the package manager of your choice (also available via `pip install "CHEM10_Harvard[test]"`). Then you can run an interactive check that walks through each component:
```bash
python -m pytest --pyargs CHEM10_Harvard -m physical -s
```
The `-s` flag is required so pytest doesn't swallow the `input()` prompts these tests use to ask you to confirm what you observe (e.g. "was the LED blinking?"). This also requires `arduino-cli` to be installed and the board to be connected and powered on.

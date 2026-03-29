

import sys
sys.path.append('../src/')

from CHEM10_Harvard.arduino_simulator import ArduinoBoard
from CHEM10_Harvard.calibration import Calibration


with Calibration(
    pin_servowrite=9,
    pin_servoread=0,
    board_class=ArduinoBoard,
    path_lut="servo_lut.json",
) as cal:
    
    cal.calibrate(angles=(30, 180), step=5)
    
    angle, error = cal.getAngle(350)
    print(f"Estimated angle = {angle:.2f} +/- {error:.2f} deg")

    cal.plot()



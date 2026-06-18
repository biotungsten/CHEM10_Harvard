
"""
    servo.py
    06/17/2026
    AW, DS, MC
"""




import json
import pandas as pd
import matplotlib.pyplot as plt




"""
    Spectrometer postprocessing.
    Functionality for basic postprocessing of spectrometer data.
"""
class Post:
    def __init__(
        self,
        blank,
        ref,
        data=None,
    ):
        self.blank = blank # json of blank curve
        self.ref = ref # json of reference LED spectrum
        self.data = data # json of experiment, optional

        


    

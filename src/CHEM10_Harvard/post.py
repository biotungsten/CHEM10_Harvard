


"""
    Spectrometer calibration.

    Maps angle to wavelength given LED reference and blank spectra.
"""
class Calibration:
    # Track servo pin user counts per board identity. Keyed by id(board). Then keyed by servo pin number. Value is user count.
    _initialized_servo_pins = {}

    def __init__(
        self,
        path_ref="servo_lut.json",
        path_blank="blank.json"
    ):
        self.board = board
        self.pin_servowrite = pin_servowrite
        self.pin_servoread = pin_servoread
        self.path_lut = Path(path_lut) # lookup table saved json path
        self.lut = {} # lookup table dict
        self._closed = False
        self._board_key = id(self.board)

        self._register_servo()


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc, tb):
        self.close()

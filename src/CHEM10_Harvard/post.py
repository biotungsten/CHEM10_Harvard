


"""
    Spectrometer postprocessing.

    Maps angle to wavelength given LED reference and blank spectra.
"""
class Post:

    def __init__(
        self,
        blank,
        data,
        ref=,
    ):
        self.data = data


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc, tb):
        self.close()

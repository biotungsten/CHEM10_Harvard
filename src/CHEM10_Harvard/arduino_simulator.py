import random

"""
    Dummy Arduino simulates functionality of arduino.py for downstream code testing without hardware.
"""
class ArduinoBoard:
    def __init__(self, address=None):
        self.address = address
        self._pin_servowrite = None
        self._pin_servoread = None
        self._angle = 10.0
        self._servo_initialized = False
        self._shutdown = False


    def initialize_servo(self, pin):
        self._pin_servowrite = pin
        self._servo_initialized = True


    def detach_servo(self, pin):
        if pin == self._pin_servowrite:
            self._servo_initialized = False


    def write_servo(self, pin, angle):
        if self._shutdown:
            raise RuntimeError("Board is shut down.")
        if not self._servo_initialized:
            raise RuntimeError("Servo not initialized.")
        if pin != self._pin_servowrite:
            raise ValueError(f"Servo not initialized on pin {pin}.")
        if angle < 10 or angle > 180:
            raise ValueError(f"Servo angle must be between 10 and 180, got {angle}.")
        self._angle = float(angle)


    def analog_read(self, pin, differential=0):
        if self._shutdown: raise RuntimeError("Board is shut down.")

        self._pin_servoread = pin
        angle = self._angle
        base = 120 + 4.2 * angle + 0.01 * (angle - 95) ** 2
        noise = random.gauss(0, 1.5)

        reading = base + noise
        # Clamp to a typical 10-bit ADC range.
        reading = max(0, min(1023, reading))

        return reading


    def shutdown(self): self._shutdown = True



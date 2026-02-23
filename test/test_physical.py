import pytest
from CHEM10_Harvard.arduino import ArduinoBoard
import time
import numpy as np
#TODO: Servo output not reliable
#TODO: Pure analog read of non servo pin not working --> no analog input signal  (have a resistor over 5V)
@pytest.mark.physical
class TestArduinoFunctions:
    LED_PIN = 8
    SERVO_PIN = 10
    SERVO_READ_PIN = 15
    DIGITAL_WRITE_PIN = 8
    DIGITAL_READ_PIN = 2
    ANALOG_WRITE_PIN = 9
    ANALOG_READ_PIN = 16

    @pytest.fixture(scope="class")
    def confirm_physical_setup_present(self):
        # This fixture is meant to confirm that the physical setup is present before running tests.
        print("\nPlease ensure that the physical setup is present and ready for testing.")
        print("Specifically, make sure that the Arduino board is connected and powered on.\nAddtionally connect LEDs, resistors, and other components as described in the documentation.")
        user_input = input("Is the physical setup present and ready for testing? (yes/no): ")
        if user_input.lower() != "yes":
            pytest.skip("Physical setup not present or not ready. Skipping tests.")
            yield None
        try:
            board = ArduinoBoard()
        except Exception as e:
            print(f"Failed to initialize Arduino board: {e}")
            pytest.skip("Failed to initialize Arduino board. Skipping tests.")
        yield board
        board.shutdown()

    def test_LED_blink(self, confirm_physical_setup_present):
        # This test will check if the LED connected to the Arduino board blinks as expected.
        print("Please observe the LED connected to the Arduino board. It should be blinking on and off at regular intervals.")
        time.sleep(2)  # Give the user time to prepare for observation

        board = confirm_physical_setup_present
        for i in range(5):
            board.digital_write(self.LED_PIN, 1)
            time.sleep(0.5)
            board.digital_write(self.LED_PIN, 0)
            time.sleep(0.5)

        user_input = input("Was the LED blinking as expected? (yes/no): ")
        assert user_input.lower() == "yes"
        
    def test_digital_read_write(self, confirm_physical_setup_present):
        board = confirm_physical_setup_present
        assert board.digital_write(self.DIGITAL_WRITE_PIN, 1) == None # Check output functionality of digital_write
        time.sleep(0.1)
        value = board.digital_read(self.DIGITAL_READ_PIN)  
        assert value == 1, f"Expected to read HIGH (1) from pin {self.DIGITAL_READ_PIN}, but got LOW (0)."

        assert board.digital_write(self.DIGITAL_WRITE_PIN, 0) == None # Check output functionality of digital_write
        time.sleep(0.1)
        value = board.digital_read(self.DIGITAL_READ_PIN) 
        assert value == 0, f"Expected to read LOW (0) from pin {self.DIGITAL_READ_PIN}, but got HIGH (1)."

    def test_analog_write(self, confirm_physical_setup_present):
        board = confirm_physical_setup_present
        for _ in range(3):
            for value in [0, 128, 140, 255]:
                assert board.analog_write(self.ANALOG_WRITE_PIN, value) == None # Check output functionality of analog_write

    def test_servo(self, confirm_physical_setup_present):
        board = confirm_physical_setup_present
        board.initialize_servo(self.SERVO_PIN)
        for angle in range(65, 180, 10):
            assert board.write_servo(self.SERVO_PIN, angle) == None # Check output functionality of write_servo
            time.sleep(0.1)  # Give the servo time to move to the new position
        board.detach_servo(self.SERVO_PIN)
        user_input = input("Did the servo move from a center postion clockwise by approximately 90 degrees? (yes/no): ")
        assert user_input.lower() == "yes"
    
    def test_servo_read(self, confirm_physical_setup_present):
        board = confirm_physical_setup_present
        angles = [60, 80, 100, 120, 140, 160]
        voltages = [220, 260, 300, 340, 380, 420]  # These values are based on the calibration curve for the specific servo and setup
        delta = 20 # Allowable error in the read values (absolute difference)
        board.initialize_servo(self.SERVO_PIN)
        for i, angle in enumerate(angles):
            board.write_servo(self.SERVO_PIN, angle)
            time.sleep(0.2)  # Give the servo time to move to the new position
            read_angle = board.analog_read(self.SERVO_READ_PIN, differential=5)
            assert abs(read_angle - voltages[i]) < delta, f"Expected to read approximately {voltages[i]} from pin {self.SERVO_READ_PIN}, but got {read_angle}."
        board.detach_servo(self.SERVO_PIN)

    def test_servo_fails_on_false_angles(self, confirm_physical_setup_present):
        invalid_angles = [5, 190, -10]
        board = confirm_physical_setup_present
        board.initialize_servo(self.SERVO_PIN)
        for angle in invalid_angles:
            assert board.write_servo(self.SERVO_PIN, angle) == -1  # Invalid angle
        board.detach_servo(self.SERVO_PIN)

    def test_digital_write_fails_on_invalid_values(self, confirm_physical_setup_present):
        board = confirm_physical_setup_present
        assert board.digital_write(self.DIGITAL_WRITE_PIN, 2) == -1  # Invalid value
        assert board.digital_write(self.DIGITAL_WRITE_PIN, -1) == -1  # Invalid value

    def test_analog_write_fails_on_invalid_values(self, confirm_physical_setup_present):
        board = confirm_physical_setup_present
        assert board.analog_write(self.ANALOG_WRITE_PIN, 256) == -1  # Invalid value
        assert board.analog_write(self.ANALOG_WRITE_PIN, -1) == -1  # Invalid value
        assert board.analog_write(self.ANALOG_WRITE_PIN, 3.14) == -1  # Invalid value (not an integer)
    
    def test_protection_against_two_instances(self, confirm_physical_setup_present):
        board = confirm_physical_setup_present
        with pytest.raises(Exception) as exc_info:
            second_board = ArduinoBoard()
        assert "An ArduinoBoard instance with address" in str(exc_info.value)
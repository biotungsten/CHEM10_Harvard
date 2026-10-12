def analog_value_to_voltage(analog_read_value, reference_voltage=5.0, resolution=1023):
    if not analog_read_value:
        raise ValueError("Warning: analog_read_value is None.")
    return (analog_read_value / resolution) * reference_voltage

def voltage_to_analog_value(voltage, reference_voltage=5.0, resolution=255):
    if voltage < 0 or voltage > reference_voltage:
        raise ValueError(f"Voltage {voltage} is out of range (0-{reference_voltage}).")
    return int((voltage / reference_voltage) * resolution)
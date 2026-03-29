def analog_value_to_voltage(analog_read_value, reference_voltage=5.0, resolution=1023):
    return (analog_read_value / resolution) * reference_voltage

def voltage_to_analog_value(voltage, reference_voltage=5.0, resolution=255):
    return int((voltage / reference_voltage) * resolution)
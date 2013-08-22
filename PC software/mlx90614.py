# From sensor manual:
MAX_READING = 0x7FFF
MIN_READING = 0x27AD

def reading2celsius(self, reading):
    celsius = reading / 50 - 273.15
    return celsius
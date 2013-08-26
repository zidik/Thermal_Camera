""" This file contains information from sensor manual"""

# maximal and minimal temperature readings
MAX_READING = 0x7FFF
MIN_READING = 0x27AD

def reading2celsius(self, reading):
    """ Converts sensor reading to celsius """
    celsius = reading / 50 - 273.15
    return celsius

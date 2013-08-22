class ThermalCamera(object):

    def __init__(self, outgoing):
        self.outgoing = outgoing

    def start_scan(self):
        self.outgoing.put_nowait("s")

    def ask_info(self):
        self.outgoing.put_nowait("i?")

    def set_Servo(self, servo_nr, value):
        if servo_nr == 0:
            output = "A"
        else:
            output = "B"
        output += "=" + str(value)

        self.outgoing.put_nowait(output)

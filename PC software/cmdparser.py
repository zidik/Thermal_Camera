import threading
import time
import queue
import logging

class CmdParser(threading.Thread):
    def __init__(self, rx, thermal_data):
        threading.Thread.__init__(self)
        self.rx = rx
        self.thermal_data = thermal_data

    def run(self):
        logging.info("Parser Starting")
        try:
            while(True):
                parsed = self.parse()
                # if there was nothing to do - sleep a bit..
                if not parsed:
                    time.sleep(0.01)
        finally:
            logging.info("Parser Stopped")

    def parse(self):
        try:
            message = self.rx.get_nowait()
        except queue.Empty:
            return False
        parsed = self.parse_CMD(message)
        return parsed

    def parse_CMD(self, cmd_string):
        cmdTokens = cmd_string.split(':')

        cmd = cmdTokens[0]
        cmd_arguments = cmdTokens[1:]

        if cmd == "Scan":
            if len(cmd_arguments) != 3:
                msg = "Serial:"
                msg += cmd_string
                msg += "\nScan command has more arguments than needed!"
                logging.warning(msg)
                return
            logging.debug("Scan command parsed")
            self.thermal_data.set_datapoint(int(cmd_arguments[0]), int(cmd_arguments[1]), int(cmd_arguments[2]))
        else:
            logging.info("Serial:", cmd_string)
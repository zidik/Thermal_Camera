import threading
import time
import queue
import logging

class CmdParser(threading.Thread):
    """ 
    Thread that parses incoming messages 
    and executes functions accordingly 
    """
    def __init__(self, rx, thermal_data):
        threading.Thread.__init__(self)
        self.rx = rx
        self.thermal_data = thermal_data

    def run(self):
        logging.info("Parser thread starting")
        try:
            while(True):
                parsed = self.parse()
                # if there was nothing to do - sleep a bit..
                if not parsed:
                    time.sleep(0.01)
        finally:
            logging.error("Parser thread stopped")

    def parse(self):
        """
        Fetches a new message from queue and tries to parse it
        returns boolean - true if message was successfully parsed
        """
        try:
            message = self.rx.get_nowait()
        except queue.Empty:
            # Nothing to parse
            return False
        parsed = self.parse_CMD(message)
        return parsed

    def parse_CMD(self, cmd_string):
        """
        Parses supplied string and executes functions accordingly
        returns boolean - true if message was successfully parsed
        """
        cmdTokens = cmd_string.split(':')

        cmd = cmdTokens[0]
        cmd_arguments = cmdTokens[1:]

        if cmd == "Scan":
            if len(cmd_arguments) == 3:
                (x, y, value) = cmd_arguments
                self.thermal_data.set_datapoint(int(x), int(y), int(value))
                return True
            else:
                logging.warning(("Serial:\"{}\"\nScan command has more arguments than needed!").format(cmd_string))
        else:
            logging.warn(("Unknown serial command recieved: \"{}\"").format(cmd_string))
        return False
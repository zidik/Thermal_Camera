# PySerial
import serial
import threading
import queue
import time
import logging


# Monitor thread -
class SerialMonitorThread(threading.Thread):
    """ Monitors serial port for incoming messages and places them in incoming queue
        and
        sends messages from outgoing queue to serial port """
    def __init__(self, serialConn, incoming, outgoing):
        threading.Thread.__init__(self)
        self.serialConn = serialConn  # Serial connection
        self.incoming = incoming  # Incoming message Queue
        self.outgoing = outgoing  # Outgoing message Queue

        self._cmdCharList = []  # List of characters that have been received (from last message start until now). This list is emptied if message stop sign is received

    def run(self):
        logging.info("SerialThread Starting")
        outgoingMessage = None  # Message that is currently being sent over serial

        while(True):
            idle = True  # stays true if nothing is done in this cycle
            if self.serialConn.isOpen():
                # Fetch a new message from queue if needed
                if outgoingMessage is None:
                    try:
                        outgoingMessage = self.outgoing.get_nowait()
                    except queue.Empty:
                        pass
                # if message is fetched, send it
                if outgoingMessage is not None:
                    sent = self.sendCMD(outgoingMessage)
                    if sent:
                        outgoingMessage = None
                        idle = False
                # read incoming serial
                bytesRead = self.readCMD()
                if bytesRead > 0:
                    idle = False

            # if there was nothing to do - sleep a bit..
            if idle:
                time.sleep(0.01)

        logging.info("SerialThread Stopped")

    def sendCMD(self, message):
        """ sends a message over serial to device
            takes message as an argument
            returns: True if writing to serial writing does not raise an exception
                     False if it does. """

        success = False
        try:
            self.serialConn.write(("<" + message + ">").encode())
            success = True
        except Exception as e:
            logging.exception(str(e))
            logging.warning("Could not write message to serial port. (" + message + ")")

        if success:
            logging.debug("Sent message: " + str(message))
            # TODO: Callback!
            self.outgoing.task_done()  # indicate, that message has been sent
        return success

    def readCMD(self):
        """reads bytes one by one from serial port and
        puts received messages to incoming Queue.
        returns: number of bytes read."""

        # cmd has started if char list is not empty
        cmdStarted = len(self._cmdCharList) > 0

        bytesRead = 0
        waitingCount = self.serialConn.inWaiting()
        while waitingCount > 0:
            # skip everything until command start sign if command has not started
            while not cmdStarted and waitingCount > 0:
                if self.serialConn.read().decode() == '<':
                    cmdStarted = True
                waitingCount -= 1
                bytesRead += 1


            while cmdStarted:
                incomingChar = self.serialConn.read().decode()
                if incomingChar == '>':
                    message = ''.join(self._cmdCharList)
                    self._cmdCharList = []
                    cmdStarted = False

                    self.incoming.put_nowait(message)
                    logging.debug("Got a message: " + str(message))
                    # TODO: Callback
                else:
                    self._cmdCharList.append(incomingChar)
                waitingCount -= 1
                bytesRead += 1

        return bytesRead

def connect_device(serial_connection, expectedResponce, infoString = None):
    """ Scans through open ports and sends infostring to them.
        Then waits for response and if it does match with expectedResponce,
        function leaves the connection open and exits 
        
        Returns a tuple
        1) Boolean indicating whether device was found
        2) list of tuples containing information about ports that were opened during search (when device is not found then this is complete list of openable ports) 
        """
    # Save current timeouts(to be recovered in the end) Set tight timeouts.
    save_timeout = (serial_connection.timeout, serial_connection.writeTimeout)
    (serial_connection.timeout, serial_connection.writeTimeout) = (0.1, 0.1)

    found = []
    for unused_variable in connect_to_next_open_port(serial_connection):  # @UnusedVariable
        if infoString is not None:
            serial_connection.write(infoString.encode())  # Send infoString
        responce = serial_connection.readline().decode()  # Collect response
        found.append((serial_connection.port, serial_connection.portstr, responce))
        if responce == expectedResponce:
            logging.info("Found the device!")
            success = True
            break
    else:
        msg = "Could not find the device\nDevices i saw:\n"
        for (port, portStr, responce) in found:
            msg += '  - PortNr:{}, PortString:"{}", Responce:"{}"\n'.format(port, portStr, responce)
        logging.warn(msg)
        success = False

    (serial_connection.timeout, serial_connection.writeTimeout) = save_timeout
    return (success, found)

def connect_to_next_open_port(serial_connection, min_port = 0, max_port = 255):
    """Generator - every iteration opens next open port with serial_connection"""
    for port_nr in range(min_port, max_port + 1):
        if serial_connection.isOpen():
            serial_connection.close()
        serial_connection.port = port_nr
        try:
            serial_connection.open()
            # port is successfully opened if no exception is raised here
            yield
        except serial.SerialException:
            pass


import mlx90614 as sensor
import numpy as np

class Observable(object):
    """
        Subclassing this class will make objects "observable"
        calling notify() on "observable" object will call update_notification() function on every other object who is attached to it.
        all observers should be attached to observable object trough attach(observer) function.
        """
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        if not observer in self._observers:
            self._observers.append(observer)
        else:
            raise ValueError("Observer already in list")

    def detach(self, observer):
        self._observers.remove(observer)

    def notify(self):
        for observer in self._observers:
            observer.update_notification()
            # self could be sent also for source identification
            # observer.update_notification(self)


class ThermalData(Observable):

    def __init__(self, size):
        Observable.__init__(self)
        self.size = size

        # For testing purposes, data is initially random
        random_data = sensor.MIN_READING + np.random.random((self.size, self.size)) * (sensor.MAX_READING - sensor.MIN_READING)
        self._data = np.array(random_data)  # dtype needed? , dtype = float
        # self._data = np.zeros((self.size,self.size))

        # variables to hold maximal and minimal value encountered
        self.maximum = None
        self.minimum = None

    def set_datapoint(self, x, y, value):
        # Limit x,y and value
        if x < 0 or x >= self.size:
            raise ValueError(("x-coordinate must be between {} and {} but it is {}").format(0, self.size, x))
        if y < 0 or y >= self.size:
            raise ValueError(("y-coordinate must be between {} and {} but it is {}").format(0, self.size, y))
        if value > sensor.MAX_READING or value < sensor.MIN_READING:
            raise ValueError(("value must be between MIN({}) and MAX({}) but it is {}").format(sensor.MIN_READING, sensor.MAX_READING, value))

        # Remember maximum value in image
        if self.maximum == None or self.maximum < value:
            self.maximum = value
        if self.minimum == None or self.minimum > value:
            self.minimum = value

        # set data-point and notify observers of change
        self._data[y][x] = value
        self.notify()

    def clear_data(self):
        self._data.fill(0)
        self.notify()

    @property
    def data(self):
        """
        NB! Shouldn't be used to change contents of data.
        If really needed, don't forget to call notify()
        """
        return self._data

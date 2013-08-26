'''
Created on 04.07.2013

@author: Mark
'''
# # Imports
import logging

import numpy as np

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Tkinter
import tkinter as tk
from tkinter import ttk

# PySerial
import serial
import serialHelpers

import queue

import mlx90614 as sensor

from thermaldata import ThermalData
from thermalcamera import ThermalCamera
from cmdparser import CmdParser

MAXIMUM_SHIFT = 8

class ThermalCamApp():
    def __init__(self, parent, serialThermal):
        self.parent = parent
        self.serialThermal = serialThermal

        self.connect_thermal_camera()

        self.shift_ammount = 0

        self.thermal_data = ThermalData(64)
        self.thermal_data_updated = False
        self.thermal_data.attach(self)  # attaching application as data observer (on notification, update_notification() will be called)

        incoming = queue.Queue()
        outgoing = queue.Queue()
        # Start serial monitor
        serial_monitor = serialHelpers.SerialMonitorThread(self.serialThermal, incoming, outgoing)
        serial_monitor.setDaemon(True)
        serial_monitor.start()

        # Thread that parses incoming messages and edits thermal_data accordingly
        cmd_parser = CmdParser(incoming, self.thermal_data)
        cmd_parser.setDaemon(True)
        cmd_parser.start()

        self.thermal_camera = ThermalCamera(outgoing)

        # Setup window size
        w = self.parent.winfo_screenwidth() - 20
        h = self.parent.winfo_screenheight() / 3 * 2

        # sw = self.parent.winfo_screenwidth()
        sh = self.parent.winfo_screenheight()
        # x = (sw - w) / 2
        y = (sh - h) / 2
        x = 0
        self.parent.geometry('%dx%d+%d+%d' % (w, h, x, y))
        # self.parent.geometry('%dx%d+%d+%d' % (sw - 10, sh - 100, 0, 0))
        self.parent.title("Thermal camera control")

        # Frame
        self.frame = tk.Frame(self.parent)
        self.frame.style = ttk.Style()
        self.frame.style.theme_use("default")
        self.frame.pack(fill = tk.BOTH, expand = 1)

        # Quit button
        self.quitButton = ttk.Button(self.frame, text = "QUIT", command = self.quit)
        self.quitButton.pack(side = tk.LEFT)

        # Connect button
        # self.connect_button = ttk.Button(self.frame, text = "Reconnect", command = self.thermal_cam.serial_connection.reconnect)
        # self.connect_button.pack(side = tk.LEFT)

        # Start scan button
        self.connect_button = ttk.Button(self.frame, text = "Scan", command = self.thermal_camera.start_scan)
        self.connect_button.pack(side = tk.LEFT)

        # self.serial_text_widget = scrolledtext.ScrolledText(self.frame, width = 40, height = 10, state = 'disabled', wrap = tk.WORD, font = 'helvetica 9')
        # self.serial_text_widget.pack(side = tk.LEFT)
        # self.serial_text_widget.tag_configure('incoming', background = '#8AB8E6')
        # self.serial_text_widget.tag_configure('outgoing', background = "#A3D1FF")
        # self.serial_text_widget.tag_configure('error', foreground = "red")

        # self.writeToLog("Tere! -siina olen mina!", ("incoming"))
        # self.writeToLog("Tere! -siina olen mina!", ("outgoing"))
        # self.writeToLog("Tere! -siina olen mina!", ("incoming", "error"))

        # Todo: send the variable to serial port

        self.create_servo_sliders()
        self.create_temp_limit_sliders()
        self.create_shift_slider()

        # Canvas
        # matplotlib setup
        self.fig = plt.figure(figsize = (14, 5), dpi = 100)
        self.ren_canvas = FigureCanvasTkAgg(self.fig, master = self.frame)
        self.ren_canvas.show()
        self.ren_canvas.get_tk_widget().pack()

        self.create_thermal_image()
        self.create_histogram()

        self.cycle();

    def writeToLog(self, msg, tags):
        numlines = self.serial_text_widget.index('end - 1 line').split('.')[0]
        self.serial_text_widget['state'] = 'normal'
        if numlines == 15:
            self.serial_text_widget.delete(1.0, 2.0)
        # if self.serial_text_widget.index('end-1c') != '1.0':
        #    self.serial_text_widget.insert('end', '\n')
        self.serial_text_widget.insert('end', msg + '\n', tags)
        self.serial_text_widget['state'] = 'disabled'

    def update_notification(self):
        self.thermal_data_updated = True

    def create_servo_sliders(self):
        self.servo_A_slider = ttk.Scale(self.frame,
                               from_ = 608, to = 175,
                               orient = tk.VERTICAL,
                               length = 300,
                               command = self.set_servo_A)
        self.servo_A_slider.pack(side = tk.LEFT)
        self.servo_B_slider = ttk.Scale(self.frame,
                               from_ = 608, to = 175,
                               orient = tk.VERTICAL,
                               length = 300,
                               command = self.set_servo_B)
        self.servo_B_slider.pack(side = tk.LEFT)

    def set_servo_A(self, event):
        value = round(self.servo_A_slider.get())
        self.thermal_camera.set_servo(0, value)

    def set_servo_B(self, event):
        value = round(self.servo_B_slider.get())
        self.thermal_camera.set_servo(1, value)

    def create_thermal_image(self):
        self.ax_thermal_image = self.fig.add_subplot(1, 2, 1, axisbg = 'red')
        self.ax_thermal_image.set_title("Thermal image")
        self.ax_thermal_image.get_yaxis().set_visible(False)
        self.ax_thermal_image.get_xaxis().set_visible(False)
        self.ax_thermal_image.get_axes().set_frame_on(True)

        thermal_image = self.generate_thermal_image(self.thermal_data.data)

        self.im = self.ax_thermal_image.imshow(thermal_image, cmap = 'jet', interpolation = 'bicubic', vmin = sensor.MIN_READING, vmax = sensor.MAX_READING)
        self.cbar = self.fig.colorbar(self.im)
        self.cbar.set_label('Temperature')

    def create_histogram(self):
        self.axHist = self.fig.add_subplot(1, 2, 2)
        self.axHist.set_title("Temperature data histogram")
        # self.axHist.get_yaxis().set_visible(False)

    def create_shift_slider(self):
        self.shift_slider = ttk.Scale(self.frame,
                               from_ = -MAXIMUM_SHIFT, to = MAXIMUM_SHIFT,
                               value = self.shift_ammount,
                               orient = tk.VERTICAL,
                               length = 200,
                               command = self.setShift)
        self.shift_slider.pack(side = tk.LEFT)

    def create_temp_limit_sliders(self):

        minimum = sensor.MIN_READING
        maximum = sensor.MAX_READING
        slider_length = 400

        self.temp_min_slider = ttk.Scale(self.frame,
                                       from_ = maximum, to = minimum,
                                       value = minimum,
                                       orient = tk.VERTICAL,
                                       length = slider_length,
                                       command = self.set_temp_min_slider)

        self.temp_max_slider = ttk.Scale(self.frame,
                                        from_ = maximum , to = minimum,
                                        value = maximum,
                                        orient = tk.VERTICAL,
                                        length = slider_length,
                                        command = self.set_temp_max_slider)

        self.temp_min_slider.pack(side = tk.LEFT)
        self.temp_max_slider.pack(side = tk.LEFT)

    def generate_thermal_image(self, data):
        return self.shift_correction(data, self.shift_ammount)

    def shift_correction(self, data, shift):
        """ When images are scanned, columns are get shifted because of servo movement direction.
            This method shifts data columns back.
            Warning - messes up original data(give it a copy of original) """
        # NOT ANYMORE! :)
        templist = []
        # transpose to access columns instead of rows with "roll"
        for row in np.transpose(data):
            # Kui paarisarv, siis liigutame kumbagi rida poole v6rra (shift on kordamooda posi- ja negatiivne)
            # Kui paaritu, siis yhele poole yhe v6rra rohkem, kui teisel poole (negatiivse shifti puhul, muutub jagatava abs.v22rtus suuremaks ja positiivse puhul v2iksemaks)
            shift_ammount = (shift - (shift % 2)) // 2
            # delete over-rolling data
            for index in range(min(0, -shift_ammount), max(0, -shift_ammount)):
                pass
                # row[index] = -1
            # roll
            templist.append(np.roll(row, shift_ammount))
            shift = -shift

        # transpose array back to original and return
        return np.transpose(np.array(templist))

    def quit(self):
        # TODO : Cancel all pending starts (tk.after)
        self.exited = True
        self.parent.destroy()

    def cycle(self):
        if self.thermal_data_updated:
            self.thermal_data_updated = False

            thermal_image = self.generate_thermal_image(self.thermal_data.data)
            self.im.set_data(thermal_image)

            self.redraw_histogram(thermal_image)

            # TODO: Remove hack +10/-10
            if self.thermal_data.maximum is not None:
                self.temp_max_slider["from"] = self.thermal_data.maximum + 10
                self.temp_min_slider["from"] = self.thermal_data.maximum + 10
            if self.thermal_data.minimum is not None:
                self.temp_max_slider["to"] = self.thermal_data.minimum - 10
                self.temp_min_slider["to"] = self.thermal_data.minimum - 10


            self.ren_canvas.draw()

        self.parent.after(50, self.cycle)

    def redraw_histogram(self, data):
        self.axHist.clear()
        self.axHist.hist(np.ravel(data),
                         64,
                         range = [self.temp_min_slider.get(), self.temp_max_slider.get()],
                         facecolor = 'MidnightBlue',
                         edgecolor = 'black')  #  , histtype='stepfilled'
        self.axHist.set_xlim([self.temp_min_slider.get(), self.temp_max_slider.get()])

    def start_scan(self):
        self.thermal_data.clear_data()
        self.thermal_cam.start_scan()

    def set_temp_min_slider(self, event):
        minT = self.temp_min_slider.get()
        maxT = self.temp_max_slider.get()
        # If user tries to move slider past the other one, move the other one too, so that (max > min)
        if minT >= maxT:
            maxT = minT + 100
            # If it is not possible to move the other one anymore stop the current one too.
            if maxT > sensor.MAX_READING:
                maxT = sensor.MAX_READING
                minT = maxT - 100
                self.temp_min_slider.set(minT)
            self.temp_max_slider.set(maxT)
        self.setTemp(minT, maxT)

    def set_temp_max_slider(self, event):
        minT = self.temp_min_slider.get()
        maxT = self.temp_max_slider.get()
        # If user tries to move slider past the other one, move the other one too, so that (max > min)
        if maxT <= minT:
            minT = maxT - 100
            # If it is not possible to move the other one anymore stop the current one too.
            if minT < sensor.MIN_READING:
                minT = sensor.MIN_READING
                maxT = minT + 100
                self.temp_max_slider.set(maxT)
            self.temp_min_slider.set(minT)
        self.setTemp(minT, maxT)


    def setTemp(self, minT, maxT):
        self.cbar.norm.vmin = minT
        self.cbar.norm.vmax = maxT
        # TODO: siin peaks olema veidi kenam uuendamise lahendus
        self.cbar.draw_all()
        self.im.set_norm(self.cbar.norm)

        self.axHist.set_xlim([minT, maxT])

        self.ren_canvas.draw()

        self.thermal_data_updated = True
        # Why does the next one also work??
        # self.cbar.patch.figure.canvas.draw()

    def setShift(self, event):
        self.shift_ammount = round(self.shift_slider.get())
        self.thermal_data_updated = True;

    def connect_thermal_camera(self):
        serialHelpers.connect_device(self.serialThermal, "<INFO:dev=ThermalCamera>\r\n", "<i?>")



def main():
    logging.basicConfig(format = '%(levelname)s:%(message)s', level = logging.INFO)

    with serial.Serial(timeout = 0, writeTimeout = 0) as serialThermal:
        root = tk.Tk()
        ThermalCamApp(root, serialThermal)
        root.mainloop()


if __name__ == '__main__':
    main()

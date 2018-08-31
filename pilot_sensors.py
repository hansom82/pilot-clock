#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Sensors library of pilotClock project
# (c) Hansom 2018


import os
import time
import array
import feedparser
from multiprocessing import Process, Value, Array as MpArray
from ctypes import *
from pilot_sound import PilotAlarms

if os.name is not 'nt':
    from smbus2 import SMBus


class PilotSensors(object):
    # _rss_feed_src = './habrahabr.xml'
    # _rss_refrash_int = 60 # in seconds
    # _rss_feed_src = 'https://habr.com/rss/feed/posts/all/d4612c3aef7fd96c013d00f3bfc6b66c/'
    _rss_feed_src = 'https://news.yandex.ru/index.rss'
    _rss_refrash_int = 300  # in seconds
    _alarms = PilotAlarms()
    _alarm_proc = None
    _alarm_in_reproduction = Value(c_bool, False)

    _photores_approx_arr = []
    _photores_DEV_ADDR = 0x48
    _adc_channels = {
        'AIN0': 0b1000000,  # 0x40 (photo-resistor)
        'AIN1': 0b1000001,  # 0x41 (not connected)
        'AIN2': 0b1000010,  # 0x42 (not connected)
        'AIN3': 0b1000011,  # 0x43 (not connected)
    }
    _dac_channel = 0b1000000  # 0x40

    _therm_sensors_base_dir = '/sys/devices/w1_bus_master1'
    _therm_sensor_ids = ['000001ac0d2d',  # Indoor sensor ID
                         '000001ac5f3a']  # Outdoor sensor ID

    def __init__(self):
        if os.name == 'nt':
            self._devel = True
        else:
            self._devel = False
            self._bus = SMBus(1)  # 1 for RPi model B rev.2

        # Starting photoresistor process
        self._photores_proc_enable = Value(c_bool, True)
        self._photores_proc_val = Value(c_int, 0xFF)
        self._photores_proc = Process(target=self.lightProc,
                                      args=(self._photores_proc_enable, self._photores_proc_val, 20))
        self._photores_proc.start()

        # Starting RSS feed reader process
        self._rss_proc_enable = Value(c_bool, True)
        self._rss_proc_val = MpArray(c_char, bytearray(255))
        self._rss_proc = Process(target=self.rssProc,
                                 args=(self._rss_proc_enable, self._rss_proc_val, self._rss_refrash_int))
        self._rss_proc.start()

        # Starting DS18B20 thermosensors process
        self._therm_proc_enable = Value(c_bool, True)
        init_temps = [float(-99) for _ in range(len(self._therm_sensor_ids))]
        self._therm_proc_val = MpArray(c_double, init_temps)
        self._therm_proc = Process(target=self.thermProc, args=(self._therm_proc_enable, self._therm_proc_val, 60))
        self._therm_proc.start()

    def stopSensors(self):
        """
        The method of stopping all processes of sensors
        :return:
        """
        print('Stop sensors...')
        if self._alarm_proc != None and self._alarm_proc.pid is not None and self._alarm_proc.is_alive():
            self._alarm_proc.terminate()
        self._photores_proc_enable.value = False
        self._photores_proc.join()
        self._rss_proc.terminate()
        self._therm_proc_enable.value = False
        self._therm_proc.join()

    def alarm(self, atype='click'):
        """
        Method for starting process of sound reproduction
        :param atype: Sets type of sound to play
        :return:
        """
        atype = atype.lower() if type(atype) == str else 'click'
        if self._alarm_proc is not None and self._alarm_proc.pid is not None and self._alarm_proc.is_alive():
            self._alarm_proc.terminate()
        if atype == 'click':
            self._alarm_proc = Process(target=self._alarms.click, args=(self._alarm_in_reproduction,))
        elif atype == 'alarm1':
            self._alarm_proc = Process(target=self._alarms.clockAlarm, args=(self._alarm_in_reproduction, 1))
        elif atype == 'alarm2':
            self._alarm_proc = Process(target=self._alarms.clockAlarm, args=(self._alarm_in_reproduction, 2))
        if self._alarm_proc.pid is None:
            self._alarm_proc.start()

    def alarmInReproduction(self):
        """
        Method for get current state of sound reproduction flag
        :return: Current state of sound reproduction
        """
        return self._alarm_in_reproduction.value

    def getLight(self):
        """
        Method of obtaining the current value of light intensity
        :return: Integer value in range from 0 to 255
        """
        return self._photores_proc_val.value

    def lightProc(self, proc_enable, proc_val, approx_length=20):
        """
        Code of the logic for reading the ADC data to determine the light intensity
        :param proc_enable: Continued polling cycle flag
        :param proc_val: The communication variable with the main process for returning the value read from the ADC
        :param approx_length: Parameter specifying the number of values for obtaining the mean value of illumination in a time interval
        :return:
        """
        while proc_enable.value:
            if self._devel:
                proc_val.value = 255
            else:
                self._bus.write_byte(self._photores_DEV_ADDR, self._adc_channels['AIN0'])
                self._photores_approx_arr.append(self._bus.read_byte(self._photores_DEV_ADDR))
                alen = len(self._photores_approx_arr)
                approx_val = sum(self._photores_approx_arr) / alen
                if alen > approx_length:
                    self._photores_approx_arr = self._photores_approx_arr[alen - approx_length:]
                proc_val.value = 255 - int(approx_val)
            time.sleep(0.1)

    def getLastFeed(self):
        """
        The method of obtaining the last title name of a record from RSS feed
        :return: Last title name of a RSS feed
        """
        return self._rss_proc_val.value.decode('iso8859-5')

    def rssProc(self, proc_enable, proc_val, get_inerval=300):
        """
        Code of the logic for reading data from RSS feed channel
        :param proc_enable: Continued polling cycle flag
        :param proc_val: The communication variable with the main process for returning the value read RSS-channel
        :param get_inerval: Sets the polling time interval
        :return:
        """
        interval = 0
        replace_map = [('«', '"'), ('»', '"'), ('–', '-'), ('—', '-')]
        while proc_enable.value:
            if interval == 0:
                feed = feedparser.parse(self._rss_feed_src)
                feed_len = len(feed['entries'])
                if feed_len > 0:
                    last_rec_title = str(feed['entries'][0]['title']).replace('«', '"')
                    for rep in replace_map:
                        last_rec_title = last_rec_title.replace(rep[0], rep[1])
                    proc_val.value = bytes(last_rec_title[:255], encoding='iso8859-5', errors='replace')
                else:
                    proc_val.value = bytes('А новостей на сегодня больше нет... или накрылся интернет :-(',
                                           encoding='iso8859-5', errors='replace')
            interval = interval + 1 if interval <= get_inerval else 0
            time.sleep(1)

    def getTherms(self):
        """
        The method of obtaining the list of values containing data from thermal sensors
        :return: list of float values temperature
        """
        return [t for t in self._therm_proc_val]

    def thermProc(self, proc_enable, proc_val, get_interval=60):
        """
        Code of the logic for obtaining data from thermal sensors
        :param proc_enable: Continued polling cycle flag
        :param proc_val: The communication variable with the main process for returning the value obtained from thermal sensors
        :param get_interval: Sets the polling time interval
        :return:
        """
        interval = 0
        s_paths = [self._therm_sensors_base_dir + '/28-' + id + '/w1_slave' for id in self._therm_sensor_ids]
        while proc_enable.value:
            if interval == 0:
                for i, sensor in enumerate(s_paths):
                    if os.path.exists(sensor):
                        try:
                            with open(sensor, "r") as t_file:
                                tdata = t_file.readlines()
                                if tdata[0].strip()[-4:].strip() == "YES":
                                    proc_val[i] = float(tdata[1].split('=')[1]) / 1000
                        except IOError:
                            pass
            interval = interval + 1 if interval <= get_interval else 0
            time.sleep(1)

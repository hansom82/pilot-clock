#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Main class library of pilotClock project
# (c) Hansom 2018

import os
import sys
import json
from math import floor, ceil
from time import sleep
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from pilot_fonts import font2bitmapFont, DIGITS_FONT_SLIM, DATE_OUT_FONT, RUN_LINE_FONT, THERM_DIGITS_FONT
from pilot_sensors import PilotSensors as Sensors

if os.name is 'nt':
    from luma.emulator.device import pygame as max7219emu

DIGITS_FONT_SLIM_B = font2bitmapFont(DIGITS_FONT_SLIM, 10)
DATE_OUT_FONT_B = font2bitmapFont(DATE_OUT_FONT, 6)
RUN_LINE_FONT_B = font2bitmapFont(RUN_LINE_FONT, 9)
THERM_DIGITS_FONT_B = font2bitmapFont(THERM_DIGITS_FONT, 7)
SCRIPT_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))
CONFIG_PATH = 'pilot-clock.conf'


def drawBText(draw, xy, txt, fill=None, font=None, align='left'):
    """
    Method for output text on display
    :param draw: Luma convas
    :param xy: Tuple of X and Y coordinates
    :param txt: Text
    :param fill: Fill mode
    :param font: Font
    :param align: Text align (left, right or center)
    :return:
    """
    font = font or RUN_LINE_FONT_B
    x, y = xy
    align = align.lower()
    if align == 'right':
        x = x - getBTextSize(txt, font)[0]
    elif align == 'center':
        x = x - getBTextSize(txt, font)[0] / 2
    for ch in txt.encode('iso8859-5', errors='replace'):
        draw.bitmap((x, y), font[ch], fill)
        x += font[ch].width


def getBTextSize(txt, font=None):
    """
    Method calculates text dimensions width and height
    :param txt:
    :param font:
    :return:
    """
    font = font or RUN_LINE_FONT_B
    src = [font[ascii_code].width for ascii_code in txt.encode('iso8859-5', errors='replace')]
    return sum(src), font[0].height


class PilotClock(object):
    _starting_song = True  # Sets whether to play the initial song when the program starts
    _news_alarm = True  # Sets whether to play alarms sound on new news in RSS-feed
    _config_accept_alarm = True  # Sets whether to play alarms when the configuration file is changed
    _mute = False

    _fps = 30
    _draw = None
    _loop = True

    # Alarm time format must be (start time, end time, [days of week])
    # days of week - is optional parameter. If not specified, then all days of week is true
    _alarm_time = []
    # _alarm_time = [(datetime.strptime("06:10:00", '%H:%M:%S'), datetime.strptime("07:10:00", '%H:%M:%S'), [0, 1, 2, 3, 4]),
    #                (datetime.strptime("17:30:00", '%H:%M:%S'), datetime.strptime("22:00:00", '%H:%M:%S'), [5, 6]),
    #                (datetime.strptime("11:00:00", '%H:%M:%S'), datetime.strptime("23:00:00", '%H:%M:%S'))]
    # Alarm clock format must be (alarm time, alarm melody number, [days of week])
    # days of week - is optional parameter. If not specified, then all days of week is true
    _alarm_clock = []
    # _alarm_clock = [(datetime.strptime("06:10", '%H:%M'), 2, [0, 1, 2, 3, 4]),
    #                 (datetime.strptime("18:30", '%H:%M'), 2, [5, 6]),
    #                 (datetime.strptime("11:00", '%H:%M'), 1)]

    _scroll_text_show_count = 3  # run line repeat show count
    _scroll_repeat_time = 10     # repeat interval in seconds

    _scroll_text = ''
    _do_scroll = False
    _scroll_text_size = (0, 0)
    _scroll_text_pos_x = 0
    _scroll_text_shows_num = 0
    _no_scroll_time = 0
    _last_scroll_time = datetime.now()
    _scroll_text_img = None
    _scroll_alarm_played = True
    _config_mtime = None

    def __init__(self):
        if os.name == 'nt':
            self._devel = True
            self._device = max7219emu(32, 32, 0, "1", "led_matrix", 2, 30)
        else:
            self._devel = False
            self._serial = spi(port=0, device=0, gpio=noop())
            self._device = max7219(self._serial, width=32, height=32, block_orientation=-90, rotate=0)
        self._logo = Image.open(os.path.join(SCRIPT_PATH, 'pclock.png'))
        self._sensors = Sensors()

    def __del__(self):
        self.stop()

    def readConfig(self, silent=False):
        """
        Method for reading configuration from a file in JSON format
        :param silent: If set to True, the confirmation signals will not play
        :return:
        """
        silent = silent if self._config_accept_alarm and not self._mute else True
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(CONFIG_PATH))
            if self._config_mtime != mtime:
                print('Config changed at {time:%d.%m.%Y %H:%M:%S}'.format(time=mtime))
                self._config_mtime = mtime
                with open(CONFIG_PATH, mode='r', encoding='utf-8') as conf:
                    cfg = json.loads(conf.read(), encoding='utf-8')
                    self._starting_song = self._starting_song if 'starting_song' not in cfg else cfg['starting_song']
                    self._news_alarm = self._news_alarm if 'news_alarm' not in cfg else cfg['news_alarm']
                    self._config_accept_alarm = self._config_accept_alarm if 'config_accept_alarm' not in cfg else cfg['config_accept_alarm']
                    if 'rss_src' in cfg:
                        self._sensors.setRSSFeedSource(cfg['rss_src'])
                    if 'alarm_time' in cfg:
                        alarm_time = []
                        for t in cfg['alarm_time']:
                            if 'start' in t and 'end' in t:
                                if 'days_of_week' in t and type(t['days_of_week']) == list:
                                    alarm_time.append((datetime.strptime(t['start'], '%H:%M:%S'),
                                                       datetime.strptime(t['end'], '%H:%M:%S'), t['days_of_week']))
                                else:
                                    alarm_time.append((datetime.strptime(t['start'], '%H:%M:%S'),
                                                       datetime.strptime(t['end'], '%H:%M:%S')))
                                self._alarm_time = alarm_time
                    if 'alarm_clock' in cfg:
                        alarm_clock = []
                        for t in cfg['alarm_clock']:
                            if 'time' in t and 'ringtone' in t:
                                if 'days_of_week' in t and type(t['days_of_week']) == list:
                                    alarm_clock.append(
                                        (datetime.strptime(t['time'], '%H:%M'), int(t['ringtone']), t['days_of_week']))
                                else:
                                    alarm_clock.append((datetime.strptime(t['time'], '%H:%M'), int(t['ringtone'])))
                                self._alarm_clock = alarm_clock
                    if not silent:
                        self._sensors.alarm('config_accept')
        except IOError:
            print("Error reading configuration file")
            if not silent:
                self._sensors.alarm('config_fail')
        except json.JSONDecodeError:
            print("Error decoding configuration file")
            if not silent:
                self._sensors.alarm('config_fail')

    def timeInRange(self, intime=datetime.now(), ranges_list=[]):
        """
        The method checks whether the date is included in the list of specified time ranges
        :param intime: Checking date
        :param ranges_list: List of time ranges
        :return: Return True if date included in any time range
        """
        if type(ranges_list) == list and len(ranges_list) > 0:
            for at in ranges_list:
                atlen = len(at)
                if type(at) == tuple and 2 <= atlen <= 3:
                    if atlen == 2 and at[0].time() <= intime.time() <= at[1].time():
                        return True
                    elif atlen == 3 and at[0].time() <= intime.time() <= at[1].time() and intime.weekday() in at[2]:
                        return True
        return False

    def isAlarmTime(self, intime=datetime.now(), times_list=[]):
        """
        Method checks if the time matches any of the alarms
        :param intime: Checking date
        :param times_list: Clock alarms list
        :return: Return True if input time equal any time in alarms list
        """
        intime = intime.replace(second=0, microsecond=0)
        if type(times_list) is list and len(times_list) > 0:
            for ct in times_list:
                ctlen = len(ct)
                if type(ct) is tuple and 2 <= ctlen <= 3:
                    if ctlen == 2 and ct[0].time() == intime.time():
                        return ct[0].time(), ct[1]
                    elif ctlen == 3 and ct[0].time() == intime.time() and intime.weekday() in ct[2]:
                        return ct[0].time(), ct[1], intime.weekday()
        return None

    def run(self):
        """
        Main program loop
        :return:
        """
        last_conf_read = datetime.now()
        self.readConfig(silent=True)
        self._mute = False if self.timeInRange(datetime.now(), self._alarm_time) else True
        print('Sound:', 'ON' if not self._mute else 'OFF')

        show_logo = True
        logo_time = 5
        logo_show_time = datetime.now()
        last_alarm_clock = None
        term_pos_y = 2
        if self._starting_song:
            if not self._mute:
                self._sensors.alarm('alarm1')
        while self._loop:
            self._mute = False if self.timeInRange(datetime.now(), self._alarm_time) else True
            alarm_clock = self.isAlarmTime(datetime.now(), self._alarm_clock)
            if alarm_clock is not None and last_alarm_clock != alarm_clock:
                last_alarm_clock = alarm_clock
                self._sensors.alarm('alarm'+str(alarm_clock[1]))

            start_time = datetime.now()
            if start_time - last_conf_read > timedelta(seconds=60):
                last_conf_read = datetime.now()
                self.readConfig()
            self._device.contrast(self._sensors.getLight())
            with canvas(self._device) as self._draw:
                if show_logo:
                    self.drawLogo(0, 6)
                    if start_time - logo_show_time >= timedelta(seconds=logo_time):
                        show_logo = False
                else:
                    if not self._do_scroll:
                        term_pos_y = term_pos_y + 2 if term_pos_y < 2 else 2
                    else:
                        term_pos_y = term_pos_y - 2 if term_pos_y > -10 else -10
                    if term_pos_y > -10:
                        self.drawTherm(1, term_pos_y, 0, 'left')
                        self.drawTherm(32, term_pos_y, 1, 'right')
                    self.drawDate(1, 11)
                    self.drawDayOfWeek(32, 11)
                    self.drawClock(0, 21)
                    self.drawSecondsLine(1, 18, 30)
                    self.drawScrollText(0, 1, self._sensors.getLastFeed())
            end_time = (datetime.now() - start_time).total_seconds()

            if self._do_scroll or term_pos_y < 2:
                if end_time < 1/self._fps:
                    sleep(1 / self._fps - end_time)
            else:
                if end_time < 0.5:
                    sleep(0.5 - end_time)

    def stop(self):
        """
        Method called when the application is terminated
        :return:
        """
        self._loop = False
        self._sensors.stopSensors()

    def drawTherm(self, x, y, sensor_num=0, align='left'):
        """
        Method of rendering the temperature from thermal sensor
        :param x: X display coordinate
        :param y: Y display coordinate
        :param sensor_num: Number of thermal sensor
        :param align: Text align
        :return:
        """
        font = THERM_DIGITS_FONT_B
        therms = self._sensors.getTherms()
        drawBText(self._draw, (x, y), str(int(ceil(therms[sensor_num])))+'~', fill='white', font=font, align=align)

    def drawClock(self, x, y):
        """
        Method of rendering the current time
        :param x: X display coordinate
        :param y: Y display coordinate
        :return:
        """
        font = DIGITS_FONT_SLIM_B
        now = datetime.now()
        even = floor(now.microsecond / 500000 % 2)
        hh = str(now.hour).zfill(2)
        mm = str(now.minute).zfill(2)
        if self._draw is not None:
            drawBText(self._draw, (x, y), hh, fill="white", font=font)
            drawBText(self._draw, (x + 17, y), mm, fill="white", font=font)
            if even:
                drawBText(self._draw, (x + 13, y), ':', fill="white", font=font)

    def drawDate(self, x, y, align='left'):
        """
        Method of rendering the current year and month
        :param x: X display coordinate
        :param y: Y display coordinate
        :param align: text align
        :return:
        """
        font = DATE_OUT_FONT_B
        now = datetime.now()
        date = '{0:02d}.{1:02d}'.format(now.day, now.month)
        if self._draw is not None:
            drawBText(self._draw, (x, y), date, fill="white", font=font, align=align)

    def drawDayOfWeek(self, x, y, align='right'):
        """
        Method of rendering the current day of week
        :param x: X display coordinate
        :param y: Y display coordinate
        :param align: text align
        :return:
        """
        font = DATE_OUT_FONT_B
        now = datetime.now()
        days = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']
        date = '{0}'.format(days[now.weekday()])
        if self._draw is not None:
            drawBText(self._draw, (x, y), date, fill="white", font=font, align=align)

    def drawSecondsLine(self, x, y, length=30):
        """
        Method of rendering the current time seconds indicator line
        :param x: X display coordinate
        :param y: Y display coordinate
        :param length: sets length of seconds line
        :return:
        """
        now = datetime.now()
        sofs = int(length/30 * now.second) - length
        sofs = sofs if sofs >= 0 else 0
        eofs = int(length/30 * now.second)
        eofs = eofs if eofs < length else length
        if self._draw is not None and sofs != eofs:
            self._draw.line([(x + sofs, y), (x + eofs - 1, y)], fill="white")

    def drawScrollText(self, x, y, text, offset=45):
        """
        Method of rendering the scrolling line text
        :param x: X display coordinate
        :param y: Y display coordinate
        :param text: Text
        :param offset: Starting text offset from left in line
        :return:
        """
        font = RUN_LINE_FONT_B
        if text != self._scroll_text:
            self._scroll_alarm_played = False
            self._scroll_text_shows_num = 0
            self._do_scroll = True
            self._scroll_text = text
            self._scroll_text_size = getBTextSize(self._scroll_text, font=font)
            self._scroll_text_img = Image.new("1", (self._scroll_text_size[0] + offset * 2, self._scroll_text_size[0]), 0)
            draw = ImageDraw.Draw(self._scroll_text_img)
            drawBText(draw, (offset, 0), self._scroll_text, fill="white", font=font)
            del draw
            self._scroll_text_pos_x = offset
        if self._do_scroll:
            if not self._scroll_alarm_played and self._news_alarm:
                if not self._mute and not self._sensors.alarmInReproduction():
                    self._sensors.alarm('click')
                self._scroll_alarm_played = True
            if self._scroll_text_img is not None and self._draw is not None:
                self._no_scroll_time = 0
                image = self._scroll_text_img
                self._draw.bitmap((x, y), image.crop((self._scroll_text_pos_x - offset, 0, self._scroll_text_pos_x, 9)), fill="white")
                self._scroll_text_pos_x += 1
                if self._scroll_text_pos_x > x + self._scroll_text_size[0] + offset * 2:
                    self._last_scroll_time = datetime.now()
                    self._do_scroll = False
                    self._scroll_text_pos_x = offset
            else:
                self._do_scroll = False
                self._scroll_text_pos_x = offset
        else:
            self._no_scroll_time = datetime.now() - self._last_scroll_time
            if self._scroll_text_shows_num < self._scroll_text_show_count and self._no_scroll_time.seconds > self._scroll_repeat_time and self._scroll_text != '':
                self._do_scroll = True
                self._scroll_text_shows_num += 1

    def drawLogo(self, x, y):
        if self._draw is not None:
            self._draw.bitmap((x, y), self._logo, fill="white")

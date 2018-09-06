#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Sound library of pilotClock project
# (c) Hansom 2018


import os
from time import sleep

if os.name == 'nt':
    import winsound
else:
    import RPi.GPIO as GPIO

_devel = True if os.name == 'nt' else False

# Note-Octave-Duration (1 - 1 sec, 2 - 1/2 sec, 4 - 1/4 sec, 8 - 1/8 sec, 16 - 1/16 sec)
# Pause-Duration
FAIRY_TALE = "A-0-4 D-1-4 F-1-4 A-1-4 G-1-2 G-1-4 F-1-4 E-1-2 A-1-4 \
  G-1-4 A-1-2 D-1-2 A-0-4 D-1-4 F-1-4 A-1-4 G-1-2 G-1-4 F-1-4 E-1-2 \
  A-1-4 G-1-4 A-1-1 D-2-4 C-2-4 H-1-4 A-1-4 D-2-2 G-1-2 G-1-2 F-2-4 \
  E-2-4 D-2-2 A-1-2 A-1-2 C-2-4 H-1-4 A-1-4 G-1-4 F-1-4 E-1-4 D-1-2 \
  D-1-2 D-1-1 P-1"

MERRY_CHRISTMAS = "G-1-4  C-2-4 C-2-8 D-2-8 C-2-8 H-1-8  A-1-4 A-1-4 A-1-4\
    D-2-4 D-2-8 E-2-8 D-2-8 C-2-8  H-1-4 G-1-4 H-1-4  E-2-4 E-2-8 F-2-8 E-2-8 D-2-8\
    C-2-4 A-1-4 G-1-8 G-1-8 A-1-4 D-2-4 H-1-4 C-2-2 \
    G-1-4  C-2-4 C-2-8 D-2-8 C-2-8 H-1-8  A-1-4 A-1-4 A-1-4\
    D-2-4 D-2-8 E-2-8 D-2-8 C-2-8  H-1-4 G-1-4 H-1-4  E-2-4 E-2-8 F-2-8 E-2-8 D-2-8\
    C-2-4 A-1-4 G-1-8 G-1-8 A-1-4 D-2-4 H-1-4 C-2-2\
    G-1-4  C-2-4 C-2-8 D-2-8 C-2-8 H-1-8  A-1-4 A-1-4 A-1-4\
    D-2-4 D-2-8 E-2-8 D-2-8 C-2-8  H-1-4 G-1-4 H-1-4  E-2-4 E-2-8 F-2-8 E-2-8 D-2-8\
    C-2-4 A-1-4 G-1-8 G-1-8 A-1-4 D-2-4 H-1-4 C-2-2\
    G-1-4  C-2-4 C-2-8 D-2-8 C-2-8 H-1-8  A-1-4 A-1-4 A-1-4\
    D-2-4 D-2-8 E-2-8 D-2-8 C-2-8  H-1-4 G-1-4 H-1-4  E-2-4 E-2-8 F-2-8 E-2-8 D-2-8\
    C-2-4 A-1-4 G-1-8 G-1-8 A-1-4 D-2-4 H-1-4 C-2-2"


class PilotSound(object):
    _pwm = None

    def __init__(self, pin=12):
        self._pin = pin
        if not _devel:
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(pin, GPIO.OUT)
            self._pwm = GPIO.PWM(12, 440)

    def beep(self, freq, duration):
        """
        Method of reproducing a sound signal with specified duration and frequency
        :param freq: Sets frequency
        :param duration: Sets duration
        :return:
        """
        if _devel:
            winsound.Beep(freq, duration)
        else:
            self._pwm.ChangeFrequency(freq)
            self._pwm.start(10)
            sleep(duration / 1000)
            self._pwm.stop()
            sleep(0.02)

    def __del__(self):
        if not _devel:
            GPIO.cleanup()

    def note(self, note, speed=1):
        """
        Method for reproducing the sound of a specific note
        :param note: Note name in format N-O-D, where N - note name, O - number of octave, D - note duration
                     For example: C-1-2 or C#.-1-4 describe note C in first octave and duration 1/4 sec + half of its duration
        :param speed: Sets the playing speed multiplier
        :return:
        """
        note = str(note).upper().split('-')
        if note[0] == 'P':
            octave = 0
            duration = int(note[1]) if note[1].isalnum() else 1
        else:
            octave = int(note[1]) if note[1].isalnum() else 0
            duration = int(note[2]) if note[2].isalnum() else 1
        note = note[0]

        dur = int(500 / speed)
        if duration == 1:
            dur = int(1000 / speed)
        elif duration == 2:
            dur = int(1000 / 2 / speed)
        elif duration == 4:
            dur = int(1000 / 4 / speed)
        elif duration == 8:
            dur = int(1000 / 8 / speed)
        elif duration == 16:
            dur = int(1000 / 16 / speed)
        elif duration == 32:
            dur = int(1000 / 32 / speed)

        octave = (octave - 1) * 12
        freq = 440

        if note[len(note) - 1] == '.':
            note = note[:len(note) - 1]
            dur = int(dur + dur / 2)

        if note == 'P':
            freq = 0
        elif note == "C":
            freq = 440 * 2 ** ((octave - 2) / 12)
        elif note == "C#":
            freq = 440 * 2 ** ((octave - 1) / 12)
        elif note == "D":
            freq = 440 * 2 ** (octave / 12)
        elif note == "D#":
            freq = 440 * 2 ** ((octave + 1) / 12)
        elif note == "E":
            freq = 440 * 2 ** ((octave + 2) / 12)
        elif note == "F":
            freq = 440 * 2 ** ((octave + 3) / 12)
        elif note == "F#":
            freq = 440 * 2 ** ((octave + 4) / 12)
        elif note == "G":
            freq = 440 * 2 ** ((octave + 5) / 12)
        elif note == "G#":
            freq = 440 * 2 ** ((octave + 6) / 12)
        elif note == "A":
            freq = 440 * 2 ** ((octave + 7) / 12)
        elif note == "B":
            freq = 440 * 2 ** ((octave + 8) / 12)
        elif note == "H":
            freq = 440 * 2 ** ((octave + 9) / 12)

        if freq > 0:
            self.beep(int(freq), dur)
        else:
            sleep(1000 / dur)

    def melody(self, melody, speed=1):
        """
        Method of reproducing a sequence of musical notes, also known as a melody
        :param melody: Sting sequence of note descriptions
        :param speed: Sets the playing speed multiplier
        :return:
        """
        for note in melody.split():
            self.note(note, speed)


# Helper class for reproducing sounds in separated process
class PilotAlarms(object):

    def clockAlarm(self, reprod, num=1):
        """
        Clock alarm method for playing melody
        :param reprod: Variable for transmitting the current sound playback state
        :param num: Melody number to play
        :return:
        """
        ps = PilotSound()
        reprod.value = True
        if num == 1:
            ps.melody(FAIRY_TALE)
        elif num == 2:
            ps.melody(MERRY_CHRISTMAS)
        reprod.value = False

    def click(self, reprod):
        ps = PilotSound()
        reprod.value = True
        ps.beep(440, 200)
        reprod.value = False

    def configAccept(self, reprod):
        ps = PilotSound()
        reprod.value = True
        ps.melody("G-2-8 G-2-8 E-2-8")
        reprod.value = False

    def configFail(self, reprod):
        ps = PilotSound()
        reprod.value = True
        ps.melody("E-1-8 C-1-2 C-1-8")
        reprod.value = False


if __name__ == "__main__":
    pst = PilotSound()
    # pst.melody(MERRY_CHRISTMAS, 1)
    # pst.melody("G-2-8 G-2-8 E-2-8")
    pst.melody("E-1-8 C-1-2 C-1-8")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# pilitClick project
#
# It is led matrix clock based on Raspberry Pi Model B rev.2
# with the following functionality:
# - Digital clocks with variable brightness depend on the level of illumination
# - Clock alarm
# - Display of temperature data from two sources (DS18B20)
# - RSS feed reader (displaying last header in feed)
#
# (c) Hansom 2018

import sys
from multiprocessing import freeze_support
from pilot import PilotClock as Clock


def main():
    pilot = Clock()
    print("Starting clock...")
    try:
        pilot.run()
    except KeyboardInterrupt:
        pass
    finally:
        pilot.stop()
        print("Program finished")


if __name__ == '__main__':
    freeze_support()
    if len(sys.argv) >= 2 and '-d' in sys.argv[1:]:
        from daemonize import Daemonize
        daemon = Daemonize(app="pilot-clock", pid='/tmp/pilot-clock-daemon.pid', action=main)
        daemon.start()
    else:
        main()

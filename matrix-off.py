#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from time import sleep
from luma.core.error import DeviceNotFoundError
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop


def matrixOff():
    retry_count = 10
    current_try = 1
    try_success = False

    print("Waiting for SPI enabled ", end='')

    serial = None
    while not try_success and current_try < retry_count:
        try:
            serial = spi(port=0, device=0, gpio=noop())
            try_success = True
            print(" OK")
        except DeviceNotFoundError:
            print(".", end='')
            current_try += 1
            sleep(0.5)
    if serial is not None:
        device = max7219(serial, width=32, height=32, block_orientation=-90, rotate=0)
        device.cleanup()
    else:
        print("Device initialization error")


if __name__ == "__main__":
    print("Leds matrix cleanup...")
    matrixOff()

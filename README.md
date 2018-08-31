## pilotClock
pilotClock - a project of digital clock using 16 8x8 LED matrixes, forming a screen with a resolution of 32x32 LEDs

The application code is written in Python. It is possible to run the application on the Windows platform in the emulation mode to easily modify the code for your own needs

#### Clock functionality
+ Clock with NTP synchronization
+ Display the date with the day of the week
+ Display of temperature from room and outdoor temperature sensors
+ Dynamic change of brightness of the display depending on illumination
+ Scrolling text displays the latest news from RSS news feed
+ Managing time intervals of the allowed sound
+ Alarm clock

#### Used hardware 
+ Raspberry Pi Model B v.2
+ 4x modules with 4 built-in matrices 8x8 LEDs controlled by MAX7219 drivers 
+ Real time clock module RTC DS1302
+ AC/DA-Converter PCF8591 with photoresistor to control the level of illumination and change the display brightness
+ Two DS18B20 temperature sensors for monitoring indoor and outdoor temperatures
+ Standard 5V PC buzzer for alerting of new news and clock alarm signal

##### Python dependencies:
When running on the Raspberry Pi under the control of Raspbian Jessie:
+ Python version 3.5 and above
    - luma.core
    - luma.led_matrix
    - feedparser
    - Pillow
    - RPi.GPIO
    - smbus2
    - spidev

When running on OS Windows for emulation and development
+ Python version 3.5 and above
    - luma.core
    - luma.emulator
    - luma.led_matrix
    - Pillow-5.2.0
    - pygame-1.9.4
    - smbus2

> To correctly launch the application under the *Windows OS*, you need to comment out the imports of **fcntl**, **termios** and **curses** in the file *[PYTHON_PATH] /Lib/site-packages/luma/emulator/device.py*
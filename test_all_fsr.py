#!/usr/bin/env python3
import spidev
import time
import RPi.GPIO as GPIO

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1350000

def read_adc(channel):
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    return ((adc[1] & 3) << 8) + adc[2]

try:
    print("4-FSR Test - Press Ctrl+C to exit")
    print("-" * 60)
    while True:
        fsr0 = read_adc(0)
        fsr1 = max(read_adc(1) -75,0) 
        fsr2 = read_adc(2)
        fsr3 = read_adc(3)
        
        print(f"FSR0: {fsr0:4d}  |  FSR1: {fsr1:4d}  |  FSR2: {fsr2:4d}  |  FSR3: {fsr3:4d}")
        time.sleep(0.2)
        
except KeyboardInterrupt:
    print("\nStopped")
finally:
    spi.close()
    GPIO.cleanup()
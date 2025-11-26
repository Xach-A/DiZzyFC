import spidev  # Library to communicate with SPI devices (MCP3008 uses SPI)
import time    # For sleep delays
import RPi.GPIO as GPIO

spi = spidev.SpiDev()  # Create SPI object
spi.open(0, 0)         # Open SPI bus 0, device 0 (CE0)
spi.max_speed_hz = 1350000  # Set SPI speed to 1.35 MHz

def read_adc(channel):
    # Send 3 bytes to MCP3008, get 3 bytes back
    # [1, (8 + channel) << 4, 0] is the command format MCP3008 expects
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    
    # MCP3008 returns 10-bit result spread across bytes 2 and 3
    # Extract and combine them into a single number (0-1023)
    return ((adc[1] & 3) << 8) + adc[2]

try:
    print("FSR Test - Press Ctrl+C to exit")
    while True:                    # Loop forever
        value = read_adc(2)       # Read from ADC channel 0
        print(f"FSR: {value}")    # Display the value
        time.sleep(0.2)           # Wait 200ms before next reading
except KeyboardInterrupt:
    print("\nStopped")
finally:
    GPIO.cleanup()
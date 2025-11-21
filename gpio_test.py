import RPi.GPIO as GPIO
import time

# Set GPIO mode to BCM (Broadcom SOC channel numbers)
GPIO.setmode(GPIO.BCM)
MOSI_PIN = 10  # MOSI (Data Out)
MISO_PIN = 9   # MISO (Data In)

try:
    GPIO.setup(MOSI_PIN, GPIO.OUT)
    GPIO.setup(MISO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    print("--- GPIO Loopback Test ---")

    # Test 1: Set MOSI HIGH (1)
    GPIO.output(MOSI_PIN, GPIO.HIGH)
    time.sleep(0.1)
    miso_high = GPIO.input(MISO_PIN)
    print(f"MOSI set HIGH (1) -> MISO read: {miso_high}")

    # Test 2: Set MOSI LOW (0)
    GPIO.output(MOSI_PIN, GPIO.LOW)
    time.sleep(0.1)
    miso_low = GPIO.input(MISO_PIN)
    print(f"MOSI set LOW (0) -> MISO read: {miso_low}")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    GPIO.cleanup()
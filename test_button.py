import RPi.GPIO as GPIO
import time

BUTTON_PIN = 26

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    while True:
        print("Output")
        print(GPIO.input(BUTTON_PIN))  # Should print 1 normally, 0 when pressed
        time.sleep(0.2)
                
except KeyboardInterrupt:
    GPIO.cleanup()
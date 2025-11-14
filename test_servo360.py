#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

SERVO_PIN = 4

GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

# Clockwise rotation
print("Spinning CLOCKWISE")
pwm.ChangeDutyCycle(2.5)  # Full speed CW
time.sleep(2)

# Stop
pwm.ChangeDutyCycle(0)  # Stop
time.sleep(1)

# Counter-clockwise rotation
print("Spinning COUNTER-CLOCKWISE")
pwm.ChangeDutyCycle(12.5)  # Full speed CCW
time.sleep(2)

# Stop
pwm.ChangeDutyCycle(0)
time.sleep(0.5)

pwm.stop()
GPIO.cleanup()
print("Done")
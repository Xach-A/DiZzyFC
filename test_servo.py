#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

SERVO_PIN = 4

GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def set_angle(angle):
    duty = 2.5 + (angle / 180.0) * 10.0
    pwm.ChangeDutyCycle(duty)

try:
    # Calibration - force to known position
    print("Calibrating to 0°...")
    set_angle(0)
    time.sleep(.75)  # Wait for servo to fully reach 0°

    print("Calibrating to 90°...")
    set_angle(90)
    time.sleep(.75)

    print("Calibrating back to 0°...")
    set_angle(0)
    time.sleep(.75)

    # # Now you KNOW it's at 0°, move from there
    # print("Moving to 90°...")
    # set_angle(90)
    # time.sleep(3)
    
    # print("Moving to 180°...")
    # set_angle(180)
    # time.sleep(3)
    
    # print("Back to 90°...")
    # set_angle(90)
    # time.sleep(3)

except KeyboardInterrupt:
    print("\nStopped")

finally:
    pwm.stop()
    GPIO.cleanup()
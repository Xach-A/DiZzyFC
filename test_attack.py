#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# Right and Left servo pins
RIGHT_SERVO_PIN = 4
LEFT_SERVO_PIN = 5 

GPIO.setmode(GPIO.BCM)
GPIO.setup(RIGHT_SERVO_PIN, GPIO.OUT)
GPIO.setup(LEFT_SERVO_PIN, GPIO.OUT)

# Set up PWM at 50Hz for both
right_pwm = GPIO.PWM(RIGHT_SERVO_PIN, 50)
left_pwm = GPIO.PWM(LEFT_SERVO_PIN, 50)

right_pwm.start(0)
left_pwm.start(0)

def set_angle(pwm, angle):
    duty = 2.5 + (angle / 180.0) * 10.0
    pwm.ChangeDutyCycle(duty)

try:
    time.sleep(1)
    print("Calibrating both arms to 0°...")
    set_angle(right_pwm, 0)
    set_angle(left_pwm, 180)   # ← mirror position
    time.sleep(0.75)

    print("Attacking forward (90°)...")
    set_angle(right_pwm, 90)
    set_angle(left_pwm, 90)    # ← mirrored servo moves forward
    time.sleep(0.75)

    print("Returning to 0°...")
    set_angle(right_pwm, 0)
    set_angle(left_pwm, 180)
    time.sleep(0.75)

except KeyboardInterrupt:
    print("\nStopped")

finally:
    right_pwm.stop()
    left_pwm.stop()
    GPIO.cleanup()

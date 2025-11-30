#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# Player 1 arms
P1_RIGHT_SERVO_PIN = 20
P1_LEFT_SERVO_PIN = 19

# Player 2 arms
P2_RIGHT_SERVO_PIN = 26
P2_LEFT_SERVO_PIN = 7

GPIO.setmode(GPIO.BCM)
GPIO.setup(P1_RIGHT_SERVO_PIN, GPIO.OUT)
GPIO.setup(P1_LEFT_SERVO_PIN, GPIO.OUT)
GPIO.setup(P2_RIGHT_SERVO_PIN, GPIO.OUT)
GPIO.setup(P2_LEFT_SERVO_PIN, GPIO.OUT)

# Set up PWM at 50Hz for all arms
p1_right_pwm = GPIO.PWM(P1_RIGHT_SERVO_PIN, 50)
p1_left_pwm = GPIO.PWM(P1_LEFT_SERVO_PIN, 50)
p2_right_pwm = GPIO.PWM(P2_RIGHT_SERVO_PIN, 50)
p2_left_pwm = GPIO.PWM(P2_LEFT_SERVO_PIN, 50)

p1_right_pwm.start(0)
p1_left_pwm.start(0)
p2_right_pwm.start(0)
p2_left_pwm.start(0)

def set_angle(pwm, angle):
    duty = 2.5 + (angle / 180.0) * 10.0
    pwm.ChangeDutyCycle(duty)

try:
    time.sleep(1)
    
    print("Calibrating all arms to neutral (0° and 180°)...")
    set_angle(p1_right_pwm, 0)
    set_angle(p1_left_pwm, 180)   # mirrored
    set_angle(p2_right_pwm, 0)
    set_angle(p2_left_pwm, 180)   # mirrored
    time.sleep(3)

    print("All arms attacking forward (90°)...")
    set_angle(p1_right_pwm, 90)
    set_angle(p1_left_pwm, 90)
    set_angle(p2_right_pwm, 90)
    set_angle(p2_left_pwm, 90)
    time.sleep(3)

    print("Returning all arms to neutral...")
    set_angle(p1_right_pwm, 0)
    set_angle(p1_left_pwm, 180)
    set_angle(p2_right_pwm, 0)
    set_angle(p2_left_pwm, 180)
    time.sleep(3)

except KeyboardInterrupt:
    print("\nStopped")

finally:
    p1_right_pwm.stop()
    p1_left_pwm.stop()
    p2_right_pwm.stop()
    p2_left_pwm.stop()
    GPIO.cleanup()
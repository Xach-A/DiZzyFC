#!/usr/bin/env python3
"""
Arm Servo Calibration Tool
Use this to find the correct neutral and attack angles for each arm
"""

import RPi.GPIO as GPIO
import time

# Arm servo pins
P1_ARM_LEFT = 19
P1_ARM_RIGHT = 20
P2_ARM_LEFT = 7
P2_ARM_RIGHT = 26

GPIO.setmode(GPIO.BCM)
GPIO.setup(P1_ARM_LEFT, GPIO.OUT)
GPIO.setup(P1_ARM_RIGHT, GPIO.OUT)
GPIO.setup(P2_ARM_LEFT, GPIO.OUT)
GPIO.setup(P2_ARM_RIGHT, GPIO.OUT)

p1_left_pwm = GPIO.PWM(P1_ARM_LEFT, 50)
p1_right_pwm = GPIO.PWM(P1_ARM_RIGHT, 50)
p2_left_pwm = GPIO.PWM(P2_ARM_LEFT, 50)
p2_right_pwm = GPIO.PWM(P2_ARM_RIGHT, 50)

p1_left_pwm.start(0)
p1_right_pwm.start(0)
p2_left_pwm.start(0)
p2_right_pwm.start(0)

def set_angle(pwm, angle):
    duty = 2.5 + (angle / 180.0) * 10.0
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.01)

def calibrate_servo(name, pwm):
    print(f"\n{'='*50}")
    print(f"Calibrating: {name}")
    print(f"{'='*50}")
    
    angles_to_test = [0, 30, 45, 60, 90, 120, 135, 150, 180]
    
    for angle in angles_to_test:
        set_angle(pwm, angle)
        time.sleep(0.5)
        response = input(f"Angle {angle}° - Is this NEUTRAL (back/resting)? (y/n/skip): ").lower()
        if response == 'y':
            neutral = angle
            break
        elif response == 'skip':
            neutral = int(input("Enter neutral angle manually (0-180): "))
            break
    else:
        neutral = int(input("Enter neutral angle manually (0-180): "))
    
    set_angle(pwm, neutral)
    print(f"Neutral set to {neutral}°")
    time.sleep(1)
    
    # Find attack position
    print("\nNow finding ATTACK position (arm extended forward)...")
    for angle in angles_to_test:
        set_angle(pwm, angle)
        time.sleep(0.5)
        response = input(f"Angle {angle}° - Is this ATTACK (punching forward)? (y/n/skip): ").lower()
        if response == 'y':
            attack = angle
            break
        elif response == 'skip':
            attack = int(input("Enter attack angle manually (0-180): "))
            break
    else:
        attack = int(input("Enter attack angle manually (0-180): "))
    
    # Test the motion
    print(f"\nTesting motion: {neutral}° → {attack}° → {neutral}°")
    for _ in range(3):
        set_angle(pwm, neutral)
        time.sleep(0.4)
        set_angle(pwm, attack)
        time.sleep(0.4)
    
    set_angle(pwm, neutral)
    pwm.ChangeDutyCycle(0)
    
    return neutral, attack

try:
    print("ARM CALIBRATION TOOL")
    print("For each servo, we'll find:")
    print("  NEUTRAL = arm at rest (back position)")
    print("  ATTACK = arm extended (punching forward)")
    print()
    
    results = {}
    
    # Calibrate each arm
    results['P1_LEFT'] = calibrate_servo("Player 1 LEFT Arm", p1_left_pwm)
    results['P1_RIGHT'] = calibrate_servo("Player 1 RIGHT Arm", p1_right_pwm)
    results['P2_LEFT'] = calibrate_servo("Player 2 LEFT Arm", p2_left_pwm)
    results['P2_RIGHT'] = calibrate_servo("Player 2 RIGHT Arm", p2_right_pwm)
    
    # Print summary
    print("\n" + "="*50)
    print("CALIBRATION COMPLETE - Copy these values:")
    print("="*50)
    print("\n# Add these to your main code:")
    print(f"P1_ARM_LEFT_NEUTRAL = {results['P1_LEFT'][0]}")
    print(f"P1_ARM_LEFT_ATTACK = {results['P1_LEFT'][1]}")
    print(f"P1_ARM_RIGHT_NEUTRAL = {results['P1_RIGHT'][0]}")
    print(f"P1_ARM_RIGHT_ATTACK = {results['P1_RIGHT'][1]}")
    print(f"P2_ARM_LEFT_NEUTRAL = {results['P2_LEFT'][0]}")
    print(f"P2_ARM_LEFT_ATTACK = {results['P2_LEFT'][1]}")
    print(f"P2_ARM_RIGHT_NEUTRAL = {results['P2_RIGHT'][0]}")
    print(f"P2_ARM_RIGHT_ATTACK = {results['P2_RIGHT'][1]}")
    
except KeyboardInterrupt:
    print("\nCalibration stopped")
finally:
    p1_left_pwm.stop()
    p1_right_pwm.stop()
    p2_left_pwm.stop()
    p2_right_pwm.stop()
    GPIO.cleanup()
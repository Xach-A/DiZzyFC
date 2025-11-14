#!/usr/bin/env python3
import RPi.GPIO as GPIO  # Library to control Pi GPIO pins
import time              # For delays

RIGHT_SERVO = 5    # RIGHT wheel servo on GPIO 5.
LEFT_SERVO = 6   # LEFT wheel servo on GPIO 6

GPIO.setmode(GPIO.BCM)              # Use BCM pin numbering (GPIO numbers, not physical pin numbers)
GPIO.setup(RIGHT_SERVO, GPIO.OUT)    # Set GPIO 5 as output
GPIO.setup(LEFT_SERVO, GPIO.OUT)   # Set GPIO 6 as output

time.sleep(5)
RIGHT_pwm = GPIO.PWM(RIGHT_SERVO, 50)   # Create PWM on GPIO 5, 50Hz frequency (servos need 50Hz)
LEFT_pwm = GPIO.PWM(LEFT_SERVO, 50) # Create PWM on GPIO 6, 50Hz frequency
RIGHT_pwm.start(0)    # Start PWM with 0% duty cycle (off).
LEFT_pwm.start(0)   # Start PWM with 0% duty cycle (off)
time.sleep(.5)
print("3")
time.sleep(.5)
print("2")
time.sleep(.5)
print("1")

# Forward
print("Moving FORWARD")
RIGHT_pwm.ChangeDutyCycle(4.9)    # 2.5% duty cycle = full speed clockwise
LEFT_pwm.ChangeDutyCycle(8.9)  # 12.5% duty cycle = full speed counter-clockwise (opposite direction because servo is mirrored)
time.sleep(.5)                   # Run for 0.5 seconds

# Stop
RIGHT_pwm.ChangeDutyCycle(0)    # 7.5% duty cycle = stop position for continuous servos
LEFT_pwm.ChangeDutyCycle(0)   # Both servos stopped
time.sleep(0.5)                  # Stay stopped for 0.5 seconds

# Backward
print("Moving BACKWARD")
RIGHT_pwm.ChangeDutyCycle(8.9)   # Reverse direction: counter-clockwise
LEFT_pwm.ChangeDutyCycle(4.9)   # Reverse direction: clockwise (opposite of RIGHT)
time.sleep(.5)                   # Run for 0.5 seconds

# Stop
RIGHT_pwm.ChangeDutyCycle(0)    # Stop both servos
LEFT_pwm.ChangeDutyCycle(0)
time.sleep(0.5)

RIGHT_pwm.stop()     # Turn off PWM signal on RIGHT servo
LEFT_pwm.stop()    # Turn off PWM signal on LEFT servo
GPIO.cleanup()      # Reset all GPIO pins to default state (important for next run)
print("Done")
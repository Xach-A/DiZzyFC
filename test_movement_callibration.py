import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.OUT)
pwm = GPIO.PWM(4, 50)

try:
    pwm.start(7)
    input("Servo running at 7.5%. Adjust pot until it stops. Press Enter when done...")
    
except KeyboardInterrupt:
    print("\nStopped by user")
    
finally:
    pwm.stop()
    GPIO.cleanup()
    print("Cleaned up")
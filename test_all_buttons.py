#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# Player 1 Controller Buttons
P1_BTN_LEFT = 17
P1_BTN_RIGHT = 27
P1_BTN_ATTACK_LEFT = 22
P1_BTN_ATTACK_RIGHT = 23

# Player 2 Controller Buttons
P2_BTN_LEFT = 24
P2_BTN_RIGHT = 25
P2_BTN_ATTACK_LEFT = 5
P2_BTN_ATTACK_RIGHT = 6

# Setup
GPIO.setmode(GPIO.BCM)
all_buttons = [
    P1_BTN_LEFT, P1_BTN_RIGHT, P1_BTN_ATTACK_LEFT, P1_BTN_ATTACK_RIGHT,
    P2_BTN_LEFT, P2_BTN_RIGHT, P2_BTN_ATTACK_LEFT, P2_BTN_ATTACK_RIGHT
]

for pin in all_buttons:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    print("Button Test - Press Ctrl+C to exit")
    print("Buttons show 1 when NOT pressed, 0 when PRESSED")
    print("-" * 80)
    
    while True:
        p1_left = GPIO.input(P1_BTN_LEFT)
        p1_right = GPIO.input(P1_BTN_RIGHT)
        p1_atk_l = GPIO.input(P1_BTN_ATTACK_LEFT)
        p1_atk_r = GPIO.input(P1_BTN_ATTACK_RIGHT)
        
        p2_left = GPIO.input(P2_BTN_LEFT)
        p2_right = GPIO.input(P2_BTN_RIGHT)
        p2_atk_l = GPIO.input(P2_BTN_ATTACK_LEFT)
        p2_atk_r = GPIO.input(P2_BTN_ATTACK_RIGHT)
        
        print(f"P1: L={p1_left} R={p1_right} AtkL={p1_atk_l} AtkR={p1_atk_r}  |  "
              f"P2: L={p2_left} R={p2_right} AtkL={p2_atk_l} AtkR={p2_atk_r}")
        
        time.sleep(0.2)
        
except KeyboardInterrupt:
    print("\nStopped")
finally:
    GPIO.cleanup()
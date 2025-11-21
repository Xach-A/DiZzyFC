#!/usr/bin/env python3
"""
DiZzy FC - Main Game Code
Two-player fighting arena with servo-controlled fighters
"""

import RPi.GPIO as GPIO
import spidev
import time

# ============== PIN CONFIGURATION ==============
# Player 1 Controller Buttons (directly to GPIO, pull-up)
P1_BTN_LEFT = 17
P1_BTN_RIGHT = 27
P1_BTN_ATTACK_LEFT = 22
P1_BTN_ATTACK_RIGHT = 23

# Player 2 Controller Buttons
P2_BTN_LEFT = 24
P2_BTN_RIGHT = 25
P2_BTN_ATTACK_LEFT = 5
P2_BTN_ATTACK_RIGHT = 6

# Start buttons (one per player, both must press)
P1_BTN_START = 16
P2_BTN_START = 26

# Player 1 Fighter Servos
P1_MOVE_LEFT = 12   # Continuous servo - left wheel
P1_MOVE_RIGHT = 13  # Continuous servo - right wheel
P1_ARM_LEFT = 19    # Positional servo - left arm
P1_ARM_RIGHT = 20   # Positional servo - right arm

# Player 2 Fighter Servos
P2_MOVE_LEFT = 21   # Continuous servo - left wheel
P2_MOVE_RIGHT = 16  # Continuous servo - right wheel
P2_ARM_LEFT = 7     # Positional servo - left arm
P2_ARM_RIGHT = 8    # Positional servo - right arm

# Force Sensors via MCP3008 (SPI)
P1_FSR_CHANNEL = 0
P2_FSR_CHANNEL = 1

# ============== GAME CONSTANTS ==============
STARTING_HP = 50
PWM_FREQ = 50  # 50Hz for servos

# Continuous servo duty cycles (calibrated)
MOVE_FORWARD = 4.9
MOVE_BACKWARD = 8.9
MOVE_STOP = 0

# Positional servo angles
ARM_NEUTRAL = 0
ARM_ATTACK = 90
ARM_NEUTRAL_MIRRORED = 180  # For opposite-facing arm

# Debounce
DEBOUNCE_MS = 50

# ============== DAMAGE THRESHOLDS ==============
def calculate_damage(force_reading):
    if force_reading < 20:
        return 0
    elif force_reading < 200:
        return 3
    elif force_reading < 400:
        return 4
    elif force_reading < 600:
        return 5
    elif force_reading < 800:
        return 6
    else:
        return 7

# ============== HARDWARE SETUP ==============
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Setup buttons with pull-up resistors
button_pins = [
    P1_BTN_LEFT, P1_BTN_RIGHT, P1_BTN_ATTACK_LEFT, P1_BTN_ATTACK_RIGHT,
    P2_BTN_LEFT, P2_BTN_RIGHT, P2_BTN_ATTACK_LEFT, P2_BTN_ATTACK_RIGHT,
    P1_BTN_START, P2_BTN_START
]
for pin in button_pins:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Setup servo pins
servo_pins = [
    P1_MOVE_LEFT, P1_MOVE_RIGHT, P1_ARM_LEFT, P1_ARM_RIGHT,
    P2_MOVE_LEFT, P2_MOVE_RIGHT, P2_ARM_LEFT, P2_ARM_RIGHT
]
for pin in servo_pins:
    GPIO.setup(pin, GPIO.OUT)

# Create PWM objects
p1_move_left_pwm = GPIO.PWM(P1_MOVE_LEFT, PWM_FREQ)
p1_move_right_pwm = GPIO.PWM(P1_MOVE_RIGHT, PWM_FREQ)
p1_arm_left_pwm = GPIO.PWM(P1_ARM_LEFT, PWM_FREQ)
p1_arm_right_pwm = GPIO.PWM(P1_ARM_RIGHT, PWM_FREQ)

p2_move_left_pwm = GPIO.PWM(P2_MOVE_LEFT, PWM_FREQ)
p2_move_right_pwm = GPIO.PWM(P2_MOVE_RIGHT, PWM_FREQ)
p2_arm_left_pwm = GPIO.PWM(P2_ARM_LEFT, PWM_FREQ)
p2_arm_right_pwm = GPIO.PWM(P2_ARM_RIGHT, PWM_FREQ)

# Start all PWM at 0
all_pwm = [
    p1_move_left_pwm, p1_move_right_pwm, p1_arm_left_pwm, p1_arm_right_pwm,
    p2_move_left_pwm, p2_move_right_pwm, p2_arm_left_pwm, p2_arm_right_pwm
]
for pwm in all_pwm:
    pwm.start(0)

# Setup SPI for MCP3008
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1350000

# ============== HELPER FUNCTIONS ==============
def read_adc(channel):
    """Read from MCP3008 ADC channel (0-7)"""
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    return ((adc[1] & 3) << 8) + adc[2]

def set_angle(pwm, angle):
    """Set positional servo to specific angle"""
    duty = 2.5 + (angle / 180.0) * 10.0
    pwm.ChangeDutyCycle(duty)

def button_pressed(pin):
    """Check if button is pressed (active low with pull-up)"""
    return GPIO.input(pin) == 0

def stop_all_movement():
    """Stop all continuous servos"""
    p1_move_left_pwm.ChangeDutyCycle(MOVE_STOP)
    p1_move_right_pwm.ChangeDutyCycle(MOVE_STOP)
    p2_move_left_pwm.ChangeDutyCycle(MOVE_STOP)
    p2_move_right_pwm.ChangeDutyCycle(MOVE_STOP)

def reset_arms():
    """Reset all arms to neutral position"""
    set_angle(p1_arm_left_pwm, ARM_NEUTRAL_MIRRORED)
    set_angle(p1_arm_right_pwm, ARM_NEUTRAL)
    set_angle(p2_arm_left_pwm, ARM_NEUTRAL)
    set_angle(p2_arm_right_pwm, ARM_NEUTRAL_MIRRORED)
    time.sleep(0.3)
    # Turn off PWM signal to prevent jitter
    for pwm in [p1_arm_left_pwm, p1_arm_right_pwm, p2_arm_left_pwm, p2_arm_right_pwm]:
        pwm.ChangeDutyCycle(0)

# ============== PLAYER CLASSES ==============
class Fighter:
    def __init__(self, name, move_left_pwm, move_right_pwm, arm_left_pwm, arm_right_pwm, 
                 fsr_channel, btn_left, btn_right, btn_atk_left, btn_atk_right, facing_right=True):
        self.name = name
        self.hp = STARTING_HP
        self.move_left_pwm = move_left_pwm
        self.move_right_pwm = move_right_pwm
        self.arm_left_pwm = arm_left_pwm
        self.arm_right_pwm = arm_right_pwm
        self.fsr_channel = fsr_channel
        self.btn_left = btn_left
        self.btn_right = btn_right
        self.btn_atk_left = btn_atk_left
        self.btn_atk_right = btn_atk_right
        self.facing_right = facing_right
        self.attacking = False
        self.last_btn_time = {btn_left: 0, btn_right: 0, btn_atk_left: 0, btn_atk_right: 0}
    
    def move_left(self):
        if self.facing_right:
            self.move_left_pwm.ChangeDutyCycle(MOVE_BACKWARD)
            self.move_right_pwm.ChangeDutyCycle(MOVE_FORWARD)
        else:
            self.move_left_pwm.ChangeDutyCycle(MOVE_FORWARD)
            self.move_right_pwm.ChangeDutyCycle(MOVE_BACKWARD)
    
    def move_right(self):
        if self.facing_right:
            self.move_left_pwm.ChangeDutyCycle(MOVE_FORWARD)
            self.move_right_pwm.ChangeDutyCycle(MOVE_BACKWARD)
        else:
            self.move_left_pwm.ChangeDutyCycle(MOVE_BACKWARD)
            self.move_right_pwm.ChangeDutyCycle(MOVE_FORWARD)
    
    def stop(self):
        self.move_left_pwm.ChangeDutyCycle(MOVE_STOP)
        self.move_right_pwm.ChangeDutyCycle(MOVE_STOP)
    
    def attack_left(self):
        if self.facing_right:
            set_angle(self.arm_left_pwm, ARM_ATTACK)
        else:
            set_angle(self.arm_left_pwm, ARM_ATTACK)
        self.attacking = True
    
    def attack_right(self):
        if self.facing_right:
            set_angle(self.arm_right_pwm, ARM_ATTACK)
        else:
            set_angle(self.arm_right_pwm, ARM_ATTACK)
        self.attacking = True
    
    def reset_left_arm(self):
        if self.facing_right:
            set_angle(self.arm_left_pwm, ARM_NEUTRAL_MIRRORED)
        else:
            set_angle(self.arm_left_pwm, ARM_NEUTRAL)
    
    def reset_right_arm(self):
        if self.facing_right:
            set_angle(self.arm_right_pwm, ARM_NEUTRAL)
        else:
            set_angle(self.arm_right_pwm, ARM_NEUTRAL_MIRRORED)
    
    def read_force(self):
        return read_adc(self.fsr_channel)
    
    def take_damage(self, amount):
        self.hp -= amount
        if self.hp < 0:
            self.hp = 0
        print(f"{self.name} took {amount} damage! HP: {self.hp}")
    
    def is_knocked_out(self):
        return self.hp <= 0

# ============== GAME LOGIC ==============
def wait_for_both_start():
    """Wait for both players to press start"""
    print("Press START buttons to begin...")
    print("Waiting for Player 1...")
    while not button_pressed(P1_BTN_START):
        time.sleep(0.05)
    print("Player 1 ready!")
    
    print("Waiting for Player 2...")
    while not button_pressed(P2_BTN_START):
        time.sleep(0.05)
    print("Player 2 ready!")

def countdown():
    """3 second countdown before fight"""
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    print("FIGHT!")

def game_loop(p1, p2):
    """Main game loop"""
    attack_duration = 0.15  # How long attack animation lasts
    
    # Separate timer for each arm
    p1_left_timer = 0
    p1_right_timer = 0
    p2_left_timer = 0
    p2_right_timer = 0
    p1_left_attacking = False
    p1_right_attacking = False
    p2_left_attacking = False
    p2_right_attacking = False
    
    # Hit cooldown - prevents multiple damage from one punch
    hit_cooldown = 0.3  # 300ms between registered hits
    p1_last_hit_time = 0
    p2_last_hit_time = 0
    
    while True:
        current_time = time.time()
        
        # ---- Player 1 Input ----
        # Movement
        if button_pressed(p1.btn_left):
            p1.move_left()
        elif button_pressed(p1.btn_right):
            p1.move_right()
        else:
            p1.stop()
        
        # Attacks - independent timers
        if button_pressed(p1.btn_atk_left) and not p1_left_attacking:
            p1.attack_left()
            p1_left_attacking = True
            p1_left_timer = current_time
        
        if button_pressed(p1.btn_atk_right) and not p1_right_attacking:
            p1.attack_right()
            p1_right_attacking = True
            p1_right_timer = current_time
        
        # Reset arms after attack duration
        if p1_left_attacking and (current_time - p1_left_timer) > attack_duration:
            p1.reset_left_arm()
            p1_left_attacking = False
        
        if p1_right_attacking and (current_time - p1_right_timer) > attack_duration:
            p1.reset_right_arm()
            p1_right_attacking = False
        
        # ---- Player 2 Input ----
        # Movement
        if button_pressed(p2.btn_left):
            p2.move_left()
        elif button_pressed(p2.btn_right):
            p2.move_right()
        else:
            p2.stop()
        
        # Attacks - independent timers
        if button_pressed(p2.btn_atk_left) and not p2_left_attacking:
            p2.attack_left()
            p2_left_attacking = True
            p2_left_timer = current_time
        
        if button_pressed(p2.btn_atk_right) and not p2_right_attacking:
            p2.attack_right()
            p2_right_attacking = True
            p2_right_timer = current_time
        
        # Reset arms after attack duration
        if p2_left_attacking and (current_time - p2_left_timer) > attack_duration:
            p2.reset_left_arm()
            p2_left_attacking = False
        
        if p2_right_attacking and (current_time - p2_right_timer) > attack_duration:
            p2.reset_right_arm()
            p2_right_attacking = False
        
        # ---- Damage Detection (with cooldown) ----
        # P1's sensor detects hits FROM P2
        if (current_time - p1_last_hit_time) > hit_cooldown:
            p1_force = p1.read_force()
            p1_damage = calculate_damage(p1_force)
            if p1_damage > 0:
                p1.take_damage(p1_damage)
                p1_last_hit_time = current_time
        
        # P2's sensor detects hits FROM P1
        if (current_time - p2_last_hit_time) > hit_cooldown:
            p2_force = p2.read_force()
            p2_damage = calculate_damage(p2_force)
            if p2_damage > 0:
                p2.take_damage(p2_damage)
                p2_last_hit_time = current_time
        
        # ---- Win Condition ----
        if p1.is_knocked_out():
            return "Player 2"
        if p2.is_knocked_out():
            return "Player 1"
        
        # Small delay for loop timing (~60Hz)
        time.sleep(0.016)

# ============== MAIN ==============
if __name__ == "__main__":
    print("=" * 40)
    print("   DiZzy FC - FIGHT NIGHT")
    print("=" * 40)
    print()
    
    # Create fighters
    player1 = Fighter(
        name="Player 1",
        move_left_pwm=p1_move_left_pwm,
        move_right_pwm=p1_move_right_pwm,
        arm_left_pwm=p1_arm_left_pwm,
        arm_right_pwm=p1_arm_right_pwm,
        fsr_channel=P1_FSR_CHANNEL,
        btn_left=P1_BTN_LEFT,
        btn_right=P1_BTN_RIGHT,
        btn_atk_left=P1_BTN_ATTACK_LEFT,
        btn_atk_right=P1_BTN_ATTACK_RIGHT,
        facing_right=True
    )
    
    player2 = Fighter(
        name="Player 2",
        move_left_pwm=p2_move_left_pwm,
        move_right_pwm=p2_move_right_pwm,
        arm_left_pwm=p2_arm_left_pwm,
        arm_right_pwm=p2_arm_right_pwm,
        fsr_channel=P2_FSR_CHANNEL,
        btn_left=P2_BTN_LEFT,
        btn_right=P2_BTN_RIGHT,
        btn_atk_left=P2_BTN_ATTACK_LEFT,
        btn_atk_right=P2_BTN_ATTACK_RIGHT,
        facing_right=False
    )
    
    try:
        # Reset arms to neutral
        print("Initializing fighters...")
        reset_arms()
        stop_all_movement()
        
        # Wait for both players
        wait_for_both_start()
        
        # Countdown
        countdown()
        
        # Main game
        winner = game_loop(player1, player2)
        
        # Game over
        stop_all_movement()
        print()
        print("=" * 40)
        print(f"   KNOCKOUT! {winner} WINS!")
        print("=" * 40)
        
    except KeyboardInterrupt:
        print("\nFight stopped - NO CONTEST")
    
    finally:
        # Cleanup
        stop_all_movement()
        for pwm in all_pwm:
            pwm.stop()
        spi.close()
        GPIO.cleanup()
        print("Cleanup complete")
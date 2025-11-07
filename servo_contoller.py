"""
Functions: move_platform(), punch(), kick(), return_to_neutral()
50Hz PWM, attack sequence: rotate 90° → hold 200ms → return → 500ms cooldown

-----PROTOTYPE GIVEN BY CHATGPT; TESTING REQUIRED-----

Servo controller for Raspberry Pi using RPi.GPIO software PWM.

Supports:
180° positional micro-servos (e.g., SG90) for limb motion (punch/kick macros)
360° continuous-rotation servos for cart wheels (left/right bursts)

Standard hobby servos expect ~50 Hz control with a pulse width near 1.0–2.0 ms.
For positional servos, map angle→pulse (0°→~1.0 ms, 180°→~2.0 ms).
For continuous servos, 1.5 ms is "stop", and offsets around that command speed
and direction. Wrap PWM in a tiny class with a lock to avoid race conditions
when multiple motions run back-to-back, and provide game-friendly macros:
punch/kick = swing to (neutral + Δ), hold, then return, with a brief cooldown.

"""

import time
import threading
from typing import Optional

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM) # Use BCM pin numbers (e.g., GPIO 17, 27, 22)
GPIO.setwarnings(False)

# ---- Helpers: pulse↔duty ----------------------------------------------------

def _pulse_to_duty(pulse_ms: float, period_ms: float = 20.0) -> float:
    """Convert a pulse width (ms) to % duty-cycle at 50 Hz (20 ms period)."""
    return (float(pulse_ms) / float(period_ms)) * 100.0

def _angle_to_pulse_ms(angle_deg: float, *, min_ms: float = 1.0, max_ms: float = 2.0) -> float:
    """Map 0..180° to [min_ms..max_ms]. Real servos may need tuning."""
    a = max(0.0, min(180.0, float(angle_deg)))
    return min_ms + (max_ms - min_ms) * (a / 180.0)

def _speed_to_pulse_ms(speed: float, *, neutral_ms: float = 1.5, span_ms: float = 0.40) -> float:
    """
    Map speed in [-1..+1] to a pulse around neutral (1.5 ms).
    span_ms determines the pulse offset at full speed (typ. 0.35–0.50 ms).
    """
    s = max(-1.0, min(1.0, float(speed)))
    return neutral_ms + span_ms * s

# ---- Core PWM wrapper -------------------------------------------------------

class ServoPWM:
    """Lightweight 50 Hz PWM wrapper around RPi.GPIO.PWM with a small thread lock."""
    def __init__(self, pin: int, *, freq_hz: float = 50.0) -> None:
        self.pin = int(pin)
        self._lock = threading.Lock()

        GPIO.setup(self.pin, GPIO.OUT)
        self._pwm = GPIO.PWM(self.pin, freq_hz)
        self._pwm.start(0.0)  # 0% duty = no pulse (idle)

    def set_pulse_ms(self, pulse_ms: float) -> None:
        """Set the instantaneous pulse width in milliseconds."""
        duty = _pulse_to_duty(pulse_ms)
        with self._lock:
            self._pwm.ChangeDutyCycle(duty)

    def stop(self) -> None:
        """Stop PWM on this pin and release it."""
        with self._lock:
            try:
                self._pwm.ChangeDutyCycle(0.0)
                self._pwm.stop()
            finally:
                GPIO.setup(self.pin, GPIO.IN)

# ---- 180° positional servo --------------------------------------------------

class LimbServo:
    """Positional servo wrapper with angle commands and a neutral pose."""
    def __init__(
        self,
        pin: int,
        *,
        neutral_deg: float = 90.0,
        min_ms: float = 1.0,
        max_ms: float = 2.0,
    ) -> None:
        self.pwm = ServoPWM(pin)
        self.neutral_deg = float(neutral_deg)
        self.min_ms = float(min_ms)
        self.max_ms = float(max_ms)

        # On construction, park at neutral (helps avoid twitch on boot)
        self.goto(self.neutral_deg)

    def goto(self, angle_deg: float) -> None:
        pulse_ms = _angle_to_pulse_ms(angle_deg, min_ms=self.min_ms, max_ms=self.max_ms)
        self.pwm.set_pulse_ms(pulse_ms)

    def neutral(self) -> None:
        self.goto(self.neutral_deg)

    def stop(self) -> None:
        self.pwm.stop()

# ---- 360° continuous-rotation servo ----------------------------------------

class WheelServo:
    """
    Continuous servo wrapper: command speed [-1..+1].
    Neutral pulse is "stop"; deviations drive direction and speed.
    """
    def __init__(
        self,
        pin: int,
        *,
        neutral_ms: float = 1.5,
        span_ms: float = 0.40,
    ) -> None:
        self.pwm = ServoPWM(pin)
        self.neutral_ms = float(neutral_ms)
        self.span_ms = float(span_ms)
        self.stop()  # ensure we're stationary

    def set_speed(self, speed: float) -> None:
        pulse_ms = _speed_to_pulse_ms(speed, neutral_ms=self.neutral_ms, span_ms=self.span_ms)
        self.pwm.set_pulse_ms(pulse_ms)

    def move(self, direction: str, *, speed: float = 0.7, duration_s: float = 0.4) -> None:
        """
        Burst movement: 'left' or 'right' for a fixed duration.
        Useful for cart nudge without needing a full state machine.
        """
        sgn = -1.0 if str(direction).lower().startswith("l") else 1.0
        self.set_speed(sgn * float(speed))
        time.sleep(float(duration_s))
        self.stop()

    def stop(self) -> None:
        self.pwm.set_pulse_ms(self.neutral_ms)

    def halt(self) -> None:
        """Hard stop and release the PWM pin."""
        self.stop()
        self.pwm.stop()

# ---- High-level macros for one fighter -------------------------------------

class FighterActuators:
    """
    High-level motions for a single fighter:
      • arm (LimbServo), leg (LimbServo), wheel (WheelServo)
      • attack macro: swing → brief hold → return → cooldown
    The internal lock serializes attacks so punch/kick don't overlap mechanically.
    """
    def __init__(self, arm_pin: int, leg_pin: int, wheel_pin: int) -> None:
        self.arm = LimbServo(arm_pin, neutral_deg=90)
        self.leg = LimbServo(leg_pin, neutral_deg=90)
        self.wheel = WheelServo(wheel_pin)
        self._attack_lock = threading.Lock()

    # Platform movement on rails
    def move_platform(self, direction: str, *, speed: float = 0.7, duration_s: float = 0.4) -> None:
        self.wheel.move(direction, speed=speed, duration_s=duration_s)

    # Attack macro (blocking by design — short and simple for gameplay scripting)
    def _attack(self, servo: LimbServo, *, swing_deg: float = 90.0, hold_ms: int = 200, cooldown_ms: int = 500) -> None:
        with self._attack_lock:
            servo.goto(servo.neutral_deg + swing_deg)       # swing forward
            time.sleep(hold_ms / 1000.0)                    # brief contact window
            servo.neutral()                                  # retract
            time.sleep(cooldown_ms / 1000.0)                # cooldown (prevents flapping)

    def punch(self, *, swing_deg: float = 90.0) -> None:
        self._attack(self.arm, swing_deg=swing_deg)

    def kick(self, *, swing_deg: float = 90.0) -> None:
        self._attack(self.leg, swing_deg=swing_deg)

    def return_to_neutral(self) -> None:
        self.arm.neutral()
        self.leg.neutral()
        self.wheel.stop()

    def shutdown(self) -> None:
        """Return servos to safe state and clean up GPIO."""
        self.return_to_neutral()
        self.arm.stop()
        self.leg.stop()
        self.wheel.halt()
        GPIO.cleanup()

# testing
'''
Usage in main:

from servo_contoller import FighterActuators

# BCM pin numbers for servo signal lines:
ARM_PIN, LEG_PIN, WHEEL_PIN = 17, 27, 22

fighter = FighterActuators(ARM_PIN, LEG_PIN, WHEEL_PIN)

# simple attack
fighter.punch(swing_deg=90)

# move cart left a bit
fighter.move_platform("left", speed=0.7, duration_s=0.3)

'''
if __name__ == "__main__":
    print("This module is intended to be imported by the game loop.")
    print("Call FighterActuators(...).punch()/kick()/move_platform(...) from your main code.")

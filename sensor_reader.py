"""
Background thread reads 8 ADC channels at 100Hz
Hit detection threshold: ADC > 100
Damage formula: damage = min(max((adc_value - 100) / 10, 5), 50)

-----PROTOTYPE GIVEN BY CHATGPT; TESTING REQUIRED-----

Piezo force sensor reader for Raspberry Pi using MCP3008 (10-bit ADC) over SPI.

Non-blocking: sampling runs in a background thread at a steady cadence (default 100 Hz)
Robust: simple debouncing for "hit" events to avoid double-counting vibrations
Game-friendly: emits compact "events" that your main loop can drain without busy-waiting

Piezo sensors create brief voltage spikes upon impact. If sampled often enough and
threshold those spikes with a short cooldown (debounce), then convert the raw ADC values
into "hit" events with a mapped damage value.

"""

import threading # For background sampling/processing
import time
import spidev  # Used for MCP3008 SPI readings; Requires: sudo apt-get install python3-spidev
from collections import deque # double-ended fast queue
from typing import Deque, Dict, Iterable, List, Tuple

class PiezoSensorReader:
    """
    Background sampler for MCP3008-connected piezo sensors.

    Event dict schema
    -----------------
    {
        "channel": int,
        "value": int,          # raw 10-bit ADC (0..1023)
        "damage": float,       # post-mapped gameplay damage
        "timestamp_ms": int    # event time in epoch ms
    }
    """

    # Default sensitivity and damage mapping
    DEFAULT_THRESHOLD = 100 # ADC level to begin counting a hit
    MIN_DAMAGE = 5.0
    MAX_DAMAGE = 50.0
    DAMAGE_DIVISOR = 10.0 # (value - threshold) / divisor

    # constructor; asterisk (*) forces constructors with arguments to be called with the associated variable rather than index
    def __init__(
        self,
        channels: Iterable[int] = (0, 1, 2, 3, 4, 5, 6, 7), # ADC channel numbers to sample (0..7).
        *,
        spi_bus: int = 0, # SPI bus index (usually 0 on Raspberry Pi).
        spi_dev: int = 0, # Chip select (0 for CE0, 1 for CE1).
        sample_hz: float = 100.0, # Sample frequency; 100 Hz is a general starting point
        threshold: int = DEFAULT_THRESHOLD, # Raw ADC threshold (0..1023). Values above this create a "hit" event.
        hit_debounce_ms: int = 100, # Minimum time between hits on the same channel.
        queue_maxlen: int = 128, # Maximum number of pending events. Oldest events are dropped when full.
        baseline_alpha: float = 0.98, # Controls high-pass filter that ignores the slow limb movement
    ) -> None:

        self.channels: Tuple[int, ...] = tuple(int(c) for c in channels)
        if not self.channels:
            raise ValueError("At least one ADC channel is required.")

        self.sample_dt: float = 1.0 / float(sample_hz)
        self.threshold: int = int(threshold)
        self.hit_debounce_ms: int = int(hit_debounce_ms)

        # Baseline filter (simple high-pass via moving baseline subtraction).
        self.baseline_alpha: float = float(baseline_alpha)
        self._baseline: Dict[int, float] = {ch: 0.0 for ch in self.channels}

        # State: last hit per channel (for debounce) and latest raw value per channel
        self._last_hit_ms: Dict[int, int] = {ch: 0 for ch in self.channels}
        self._latest: Dict[int, int] = {ch: 0 for ch in self.channels}

        # Motion-aware gating: per-channel masks and temporary threshold boosts
        self._mask_until_ms: Dict[int, int] = {ch: 0 for ch in self.channels}
        self._boost_extra: Dict[int, int] = {ch: 0 for ch in self.channels}
        self._boost_until_ms: Dict[int, int] = {ch: 0 for ch in self.channels}

        # Lock-free ring buffer of events for the main loop to pop
        self._events: Deque[dict] = deque(maxlen=queue_maxlen)

        # Thread controls
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

        # SPI setup (MCP3008 speaks SPI mode 0; 1 MHz is ample throughput)
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_dev) # CE0 by default
        self.spi.max_speed_hz = 1_000_000
        self.spi.mode = 0

    # ---- Public API ----------------------------------------------------------

    def start(self) -> None:
        """Start the sampling thread (idempotent)."""
        if not self._thread.is_alive():
            self._stop.clear()
            self._thread.start()

    def stop(self) -> None:
        """Stop the sampling thread and release SPI."""
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
        try:
            self.spi.close()
        except Exception:
            pass

    def get_latest(self, ch: int) -> int:
        """Return the most recent raw value for an ADC channel (0 if unknown)."""
        return int(self._latest.get(int(ch), 0))

    # --- Motion-aware controls (call these from servo code) ---------
    def mask_channels(self, channels: Iterable[int], duration_ms: int) -> None:
        """Ignore hits on these channels for `duration_ms` from *now*."""
        now = int(time.time() * 1000)
        for ch in channels:
            ch = int(ch)
            self._mask_until_ms[ch] = max(self._mask_until_ms.get(ch, 0), now + int(duration_ms))

    def boost_threshold(self, channels: Iterable[int], extra: int, duration_ms: int) -> None:
        """Temporarily raise threshold by `extra` ADC counts on channels.
        Less aggressive than masking; good while the limb is moving.
        """
        now = int(time.time() * 1000)
        for ch in channels:
            ch = int(ch)
            self._boost_extra[ch] = max(int(extra), self._boost_extra.get(ch, 0))
            self._boost_until_ms[ch] = max(self._boost_until_ms.get(ch, 0), now + int(duration_ms))

    def pop_events(self, max_items: int = 16) -> List[dict]:
        """
        Drain up to `max_items` events from the queue (oldest first).
        Non-blocking: returns an empty list if there are no events.
        """
        n = min(max_items, len(self._events))
        return [self._events.popleft() for _ in range(n)]

    # ---- Internals -----------------------------------------------------------

    def _read_adc(self, ch: int) -> int:
        """
        Perform a single-ended read from MCP3008 channel `ch` and return a 10-bit int.

        MCP3008 transaction (3 bytes):
          - Start bit (1)
          - Single/Diff bit (1=single-ended) + 3-bit channel (ch << 4)
          - Don't-care (0); Response packs bits 9..8 in byte 1, 7..0 in byte 2
        """
        ch = int(ch)
        if not (0 <= ch <= 7):
            raise ValueError("MCP3008 channel must be 0..7")
        resp = self.spi.xfer2([0b00000001, (0b1000 | ch) << 4, 0])
        value = ((resp[1] & 0b00000011) << 8) | resp[2]  # 10-bit value
        return value

    @classmethod
    def _map_damage(cls, val: float, thr: float) -> float:
        """
        Convert a raw ADC value to clamped damage.
        Linear ramp above threshold, with MIN/MAX clamps.
        """
        delta = max(0.0, float(val) - float(thr))
        dmg = delta / cls.DAMAGE_DIVISOR
        if dmg < cls.MIN_DAMAGE:
            dmg = cls.MIN_DAMAGE
        if dmg > cls.MAX_DAMAGE:
            dmg = cls.MAX_DAMAGE
        return dmg

    def _loop(self) -> None:
        """Sampling loop aimed at a steady `sample_dt` period (100 Hz by default)."""
        now_ms = lambda: int(time.time() * 1000)

        while not self._stop.is_set():
            t0 = time.perf_counter()
            tick_ms = now_ms()

            # Read each requested channel once per tick
            for ch in self.channels:
                val = self._read_adc(ch)
                self._latest[ch] = val

                # Update baseline: y[n] = α*y[n-1] + (1-α)*x[n]
                if 0.0 <= self.baseline_alpha < 1.0:
                    self._baseline[ch] = self.baseline_alpha * self._baseline[ch] + (1.0 - self.baseline_alpha) * val
                    signal = val - self._baseline[ch]
                else:
                    signal = float(val)

                # Respect masks and temporary threshold boosts
                if tick_ms < self._mask_until_ms[ch]:
                    continue  # fully ignore this channel during self-motion

                if tick_ms > self._boost_until_ms[ch]:
                    self._boost_extra[ch] = 0  # boost expired

                eff_thr = self.threshold + self._boost_extra[ch]

                # Threshold + debounce on the high-pass filtered signal
                if signal > eff_thr:
                    last = self._last_hit_ms[ch]
                    if tick_ms - last >= self.hit_debounce_ms:
                        self._events.append({
                            "channel": ch,
                            "value": int(val),
                            "signal": float(signal),
                            "damage": self._map_damage(signal, eff_thr),
                            "timestamp_ms": tick_ms,
                        })
                        self._last_hit_ms[ch] = tick_ms

            # Maintain cadence (compensate for SPI + loop overhead)
            elapsed = time.perf_counter() - t0
            sleep = self.sample_dt - elapsed
            if sleep > 0:
                time.sleep(sleep)
            else:
                # If we ever fall behind, don't call sleep(<negative>).
                # (Occasional misses are fine; gameplay is tolerant to jitter.)
                pass


# testing
'''
sensors = PiezoSensorReader(
    channels=(0,1,2,3),
    sample_hz=100,
    threshold=120,
    hit_debounce_ms=120,
    baseline_alpha=0.98
)

sensors.start()

'''
if __name__ == "__main__":
    print("This module is intended to be imported by the game loop.")
    print("On hardware, instantiate PiezoSensorReader(...).start() and pop events periodically.")
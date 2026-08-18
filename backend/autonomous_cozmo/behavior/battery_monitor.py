import time
import collections
import threading
from typing import Optional, Dict, Any

from core.hardware.connection import cozmo_manager


class BatteryMonitor:
    """
    Battery Telemetry Volatility Mitigation & Filter.
    Tracks a rolling time window of raw lithium battery voltage readings,
    smoothing sudden voltage sags caused by mechanical motor/lift acceleration.
    """

    DEFAULT_LOW_BATTERY_VOLTS = 3.65    # Volts threshold for docking trigger
    DEFAULT_CRITICAL_VOLTS = 3.50       # Volts threshold for emergency stop
    SMOOTHING_WINDOW_SECONDS = 10.0     # Time window required below threshold before triggering low-battery state

    def __init__(
        self,
        low_voltage_threshold: float = DEFAULT_LOW_BATTERY_VOLTS,
        critical_voltage_threshold: float = DEFAULT_CRITICAL_VOLTS,
        window_duration_s: float = SMOOTHING_WINDOW_SECONDS,
    ):
        self.low_threshold = float(low_voltage_threshold)
        self.critical_threshold = float(critical_voltage_threshold)
        self.window_duration_s = float(window_duration_s)

        # Reentrant lock to prevent deadlocks when internal methods query state
        self._lock = threading.RLock()
        # Deque storing (timestamp, raw_volts)
        self._history = collections.deque()
        self._simulated_low_battery: bool = False
        self._last_raw_voltage: float = 4.0
        self._first_time_below_threshold: Optional[float] = None

    def update_voltage(self, raw_volts: float):
        """Records a new raw voltage reading from hardware telemetry."""
        with self._lock:
            self._update_voltage_unlocked(raw_volts)

    def _update_voltage_unlocked(self, raw_volts: float):
        now = time.time()
        self._last_raw_voltage = float(raw_volts)
        self._history.append((now, float(raw_volts)))

        # Prune readings older than window_duration_s
        cutoff = now - self.window_duration_s
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

        smoothed = self._calculate_smoothed_voltage_unlocked()

        # Track duration continuously sitting below low_threshold
        if smoothed < self.low_threshold:
            if self._first_time_below_threshold is None:
                self._first_time_below_threshold = now
        else:
            self._first_time_below_threshold = None

    def _calculate_smoothed_voltage_unlocked(self) -> float:
        if not self._history:
            return self._last_raw_voltage
        total = sum(v for _, v in self._history)
        return total / len(self._history)

    def get_smoothed_voltage(self) -> float:
        """Returns the current moving-average filtered battery voltage."""
        with self._lock:
            # If robot is connected, poll live voltage directly
            cli = cozmo_manager.get_robot()
            if cli and hasattr(cli, "battery_voltage") and cli.battery_voltage is not None:
                try:
                    volts = float(cli.battery_voltage)
                    if volts > 1.0: # Valid reading
                        self._update_voltage_unlocked(volts)
                except (TypeError, ValueError):
                    pass

            if self._simulated_low_battery:
                return 3.45  # Simulated critical value

            return self._calculate_smoothed_voltage_unlocked()

    def is_battery_low(self) -> bool:
        """
        Returns True only if:
        1. Simulated low battery flag is active, OR
        2. Filtered voltage has consistently remained below low_threshold for window_duration_s.
        """
        with self._lock:
            if self._simulated_low_battery:
                return True

            # Poll live if needed
            cli = cozmo_manager.get_robot()
            if cli and hasattr(cli, "battery_voltage") and cli.battery_voltage is not None:
                try:
                    volts = float(cli.battery_voltage)
                    if volts > 1.0:
                        self._update_voltage_unlocked(volts)
                except (TypeError, ValueError):
                    pass

            if self._first_time_below_threshold is None:
                return False

            now = time.time()
            duration_below = now - self._first_time_below_threshold
            return duration_below >= self.window_duration_s

    def is_battery_critical(self) -> bool:
        """Returns True if battery is critically depleted (< 3.50V)."""
        smoothed = self.get_smoothed_voltage()
        return smoothed < self.critical_threshold or self._simulated_low_battery

    def set_simulated_low_battery(self, enabled: bool):
        """Test injection utility: forces battery monitor to report low battery."""
        with self._lock:
            self._simulated_low_battery = bool(enabled)
            if not enabled:
                self._first_time_below_threshold = None

    def get_telemetry_status(self) -> Dict[str, Any]:
        with self._lock:
            smoothed = self._calculate_smoothed_voltage_unlocked()
            now = time.time()
            duration_below = 0.0
            if self._first_time_below_threshold is not None:
                duration_below = max(0.0, now - self._first_time_below_threshold)

            return {
                "raw_voltage": self._last_raw_voltage,
                "smoothed_voltage": smoothed,
                "is_low": self._simulated_low_battery or (duration_below >= self.window_duration_s),
                "is_critical": smoothed < self.critical_threshold or self._simulated_low_battery,
                "duration_below_threshold_s": duration_below,
                "simulated": self._simulated_low_battery,
            }


# Global singleton BatteryMonitor
battery_monitor = BatteryMonitor()

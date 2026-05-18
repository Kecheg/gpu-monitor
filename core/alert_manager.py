"""Alert manager for GPU monitoring thresholds."""

from enum import Enum
from typing import Optional
from dataclasses import dataclass


class AlertLevel(Enum):
    """Alert severity levels."""
    NORMAL = "normal"
    WARNING = "warning"
    DANGER = "danger"


@dataclass
class AlertThresholds:
    """Configuration for alert thresholds."""
    gpu_util_warning: int = 90
    gpu_util_danger: int = 95
    gpu_mem_warning: int = 95
    gpu_mem_danger: int = 98
    gpu_temp_warning: int = 80
    gpu_temp_danger: int = 85
    cpu_mem_warning: int = 85
    cpu_mem_danger: int = 95


class AlertManager:
    """Manage alert thresholds and determine alert levels."""

    def __init__(self, thresholds: Optional[AlertThresholds] = None):
        self.thresholds = thresholds or AlertThresholds()

    def get_gpu_utilization_level(self, utilization: int) -> AlertLevel:
        """Get alert level for GPU utilization."""
        if utilization >= self.thresholds.gpu_util_danger:
            return AlertLevel.DANGER
        elif utilization >= self.thresholds.gpu_util_warning:
            return AlertLevel.WARNING
        return AlertLevel.NORMAL

    def get_gpu_memory_level(self, memory_percent: float) -> AlertLevel:
        """Get alert level for GPU memory usage."""
        if memory_percent >= self.thresholds.gpu_mem_danger:
            return AlertLevel.DANGER
        elif memory_percent >= self.thresholds.gpu_mem_warning:
            return AlertLevel.WARNING
        return AlertLevel.NORMAL

    def get_gpu_temperature_level(self, temperature: int) -> AlertLevel:
        """Get alert level for GPU temperature."""
        if temperature >= self.thresholds.gpu_temp_danger:
            return AlertLevel.DANGER
        elif temperature >= self.thresholds.gpu_temp_warning:
            return AlertLevel.WARNING
        return AlertLevel.NORMAL

    def get_cpu_memory_level(self, memory_percent: float) -> AlertLevel:
        """Get alert level for CPU memory usage."""
        if memory_percent >= self.thresholds.cpu_mem_danger:
            return AlertLevel.DANGER
        elif memory_percent >= self.thresholds.cpu_mem_warning:
            return AlertLevel.WARNING
        return AlertLevel.NORMAL

    def get_overall_gpu_level(self, utilization: int, memory_percent: float,
                              temperature: int) -> AlertLevel:
        """Get overall alert level for a GPU."""
        levels = [
            self.get_gpu_utilization_level(utilization),
            self.get_gpu_memory_level(memory_percent),
            self.get_gpu_temperature_level(temperature)
        ]
        # Return the highest severity level
        if AlertLevel.DANGER in levels:
            return AlertLevel.DANGER
        elif AlertLevel.WARNING in levels:
            return AlertLevel.WARNING
        return AlertLevel.NORMAL

    def get_color_pair(self, level: AlertLevel) -> int:
        """Get curses color pair for alert level."""
        # These will be mapped to curses color pairs
        color_map = {
            AlertLevel.NORMAL: 0,    # Default/White
            AlertLevel.WARNING: 1,   # Yellow
            AlertLevel.DANGER: 2,    # Red
        }
        return color_map.get(level, 0)

    def update_thresholds(self, **kwargs):
        """Update alert thresholds."""
        for key, value in kwargs.items():
            if hasattr(self.thresholds, key):
                setattr(self.thresholds, key, value)

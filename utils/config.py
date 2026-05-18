"""Configuration management module."""

import os
import yaml
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class AlertConfig:
    """Alert threshold configuration."""
    gpu_util_warning: int = 90
    gpu_util_danger: int = 95
    gpu_mem_warning: int = 95
    gpu_mem_danger: int = 98
    gpu_temp_warning: int = 80
    gpu_temp_danger: int = 85
    cpu_mem_warning: int = 85
    cpu_mem_danger: int = 95


@dataclass
class Config:
    """Main configuration class."""

    # Monitoring settings
    refresh_rate: int = 2
    gpu_count: int = 8

    # Alert settings
    alerts: AlertConfig = field(default_factory=AlertConfig)

    # Logging settings
    log_enabled: bool = True
    log_dir: str = "/var/log/gpu_monitor"
    log_retention_days: int = 7

    # Display settings
    compact_mode: bool = False
    show_pcie: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary."""
        alert_data = data.get('alerts', {})
        alerts = AlertConfig(
            gpu_util_warning=alert_data.get('gpu_util_warning', 90),
            gpu_util_danger=alert_data.get('gpu_util_danger', 95),
            gpu_mem_warning=alert_data.get('gpu_mem_warning', 95),
            gpu_mem_danger=alert_data.get('gpu_mem_danger', 98),
            gpu_temp_warning=alert_data.get('gpu_temp_warning', 80),
            gpu_temp_danger=alert_data.get('gpu_temp_danger', 85),
            cpu_mem_warning=alert_data.get('cpu_mem_warning', 85),
            cpu_mem_danger=alert_data.get('cpu_mem_danger', 95)
        )

        return cls(
            refresh_rate=data.get('refresh_rate', 2),
            gpu_count=data.get('gpu_count', 8),
            alerts=alerts,
            log_enabled=data.get('log_enabled', True),
            log_dir=data.get('log_dir', '/var/log/gpu_monitor'),
            log_retention_days=data.get('log_retention_days', 7),
            compact_mode=data.get('compact_mode', False),
            show_pcie=data.get('show_pcie', True)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Config to dictionary."""
        return {
            'refresh_rate': self.refresh_rate,
            'gpu_count': self.gpu_count,
            'alerts': {
                'gpu_util_warning': self.alerts.gpu_util_warning,
                'gpu_util_danger': self.alerts.gpu_util_danger,
                'gpu_mem_warning': self.alerts.gpu_mem_warning,
                'gpu_mem_danger': self.alerts.gpu_mem_danger,
                'gpu_temp_warning': self.alerts.gpu_temp_warning,
                'gpu_temp_danger': self.alerts.gpu_temp_danger,
                'cpu_mem_warning': self.alerts.cpu_mem_warning,
                'cpu_mem_danger': self.alerts.cpu_mem_danger,
            },
            'log_enabled': self.log_enabled,
            'log_dir': self.log_dir,
            'log_retention_days': self.log_retention_days,
            'compact_mode': self.compact_mode,
            'show_pcie': self.show_pcie
        }


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file with fallback to defaults."""
    config_paths = []

    if config_path:
        config_paths.append(config_path)

    config_paths.extend([
        os.path.expanduser("~/.config/gpu_monitor/config.yaml"),
        "/etc/gpu_monitor/config.yaml"
    ])

    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = yaml.safe_load(f)
                    if data:
                        return Config.from_dict(data)
            except (OSError, yaml.YAMLError):
                continue

    return Config()


def save_default_config(path: str):
    """Save default configuration to file."""
    config = Config()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False)

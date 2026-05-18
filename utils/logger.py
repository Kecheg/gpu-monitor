"""Logging module with daily rotation and compression."""

import os
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List


class Logger:
    """Logger with daily rotation and automatic cleanup."""

    def __init__(self, log_dir: str, retention_days: int = 7):
        self._log_dir = Path(log_dir)
        self._retention_days = retention_days
        self._current_date = None
        self._log_file = None
        self._enabled = True

    def _ensure_log_dir(self) -> bool:
        """Ensure log directory exists or create fallback."""
        if self._log_dir.exists():
            return True

        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            return True
        except (OSError, PermissionError):
            # Fallback to user local directory
            fallback = Path.home() / ".local/share/gpu_monitor"
            try:
                fallback.mkdir(parents=True, exist_ok=True)
                self._log_dir = fallback
                return True
            except (OSError, PermissionError):
                self._enabled = False
                return False

    def _get_log_path(self, date: datetime) -> Path:
        """Get log file path for a specific date."""
        return self._log_dir / f"gpu_monitor_{date.strftime('%Y%m%d')}.log"

    def _rotate_if_needed(self):
        """Rotate log file if date has changed."""
        current_date = datetime.now().date()
        if self._current_date != current_date:
            if self._log_file:
                self._log_file.close()
            self._current_date = current_date
            self._log_file = None

    def _open_log_file(self):
        """Open current day's log file."""
        if self._log_file is None:
            log_path = self._get_log_path(datetime.now())
            try:
                self._log_file = open(log_path, 'a')
            except (OSError, PermissionError):
                self._enabled = False

    def _compress_old_logs(self):
        """Compress logs older than retention period."""
        if not self._log_dir.exists():
            return

        cutoff_date = datetime.now().date() - timedelta(days=self._retention_days)

        for log_file in self._log_dir.glob("gpu_monitor_*.log"):
            try:
                # Extract date from filename
                date_str = log_file.stem.split('_')[-1]
                file_date = datetime.strptime(date_str, '%Y%m%d').date()

                if file_date < cutoff_date:
                    # Compress the file
                    gz_path = log_file.with_suffix('.log.gz')
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(gz_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    log_file.unlink()

            except (ValueError, OSError):
                continue

    def _cleanup_old_logs(self):
        """Remove compressed logs beyond retention."""
        if not self._log_dir.exists():
            return

        cutoff_date = datetime.now().date() - timedelta(days=self._retention_days + 7)

        for gz_file in self._log_dir.glob("gpu_monitor_*.log.gz"):
            try:
                date_str = gz_file.stem.split('_')[-1]
                file_date = datetime.strptime(date_str, '%Y%m%d').date()

                if file_date < cutoff_date:
                    gz_file.unlink()

            except (ValueError, OSError):
                continue

    def initialize(self):
        """Initialize the logger."""
        if not self._ensure_log_dir():
            return

        self._current_date = datetime.now().date()
        self._compress_old_logs()
        self._cleanup_old_logs()

    def log(self, message: str):
        """Write a log message."""
        if not self._enabled:
            return

        self._rotate_if_needed()
        self._open_log_file()

        if self._log_file and not self._log_file.closed:
            try:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self._log_file.write(f"{timestamp} | {message}\n")
                self._log_file.flush()
            except (OSError, IOError):
                self._enabled = False

    def log_gpu_data(self, gpus: List, cpu_memory, processes: List):
        """Log formatted GPU monitoring data."""
        if not self._enabled:
            return

        parts = []
        for gpu in gpus:
            if hasattr(gpu, 'offline') and gpu.offline:
                parts.append(f"GPU{gpu.gpu_id}: Offline")
            else:
                mem_pct = gpu.memory_percent
                parts.append(
                    f"GPU{gpu.gpu_id}: Mem={gpu.memory_used}/{gpu.memory_total}MB("
                    f"{mem_pct:.1f}%), Util={gpu.utilization}%, "
                    f"Temp={gpu.temperature}°C, Power={gpu.power:.0f}W, "
                    f"PCIe-TX={gpu.pcie_tx:.1f}MB/s, PCIe-RX={gpu.pcie_rx:.1f}MB/s"
                )

        cpu_part = f"CPU: {cpu_memory.used_mb}/{cpu_memory.total_mb}MB({cpu_memory.percent:.1f}%)"

        proc_parts = []
        for proc in processes[:3]:
            proc_parts.append(
                f"PID={proc.pid}, Name={proc.name}, GPU={proc.gpu_id}, "
                f"Mem={proc.memory_mb}MB"
            )

        proc_str = " | ".join(proc_parts) if proc_parts else "None"

        self.log(" | ".join(parts) + f" | {cpu_part} | TopProcess: {proc_str}")

    def close(self):
        """Close the log file."""
        if self._log_file:
            self._log_file.close()
            self._log_file = None

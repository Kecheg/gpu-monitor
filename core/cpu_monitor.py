"""CPU and memory monitoring module."""

import subprocess
import psutil
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ProcessInfo:
    """Data class for process information."""
    pid: int
    name: str
    gpu_id: int
    memory_mb: int


@dataclass
class MemoryInfo:
    """Data class for system memory information."""
    total_mb: int
    used_mb: int
    available_mb: int
    percent: float


class CPUMonitor:
    """Monitor CPU memory and GPU processes."""

    def __init__(self, top_n: int = 5):
        self._top_n = top_n
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the CPU monitor."""
        self._initialized = True
        return True

    def get_memory_info(self) -> MemoryInfo:
        """Get system memory information."""
        try:
            mem = psutil.virtual_memory()
            return MemoryInfo(
                total_mb=mem.total // (1024 * 1024),
                used_mb=mem.used // (1024 * 1024),
                available_mb=mem.available // (1024 * 1024),
                percent=mem.percent
            )
        except Exception:
            return MemoryInfo(total_mb=0, used_mb=0, available_mb=0, percent=0)

    def get_gpu_processes(self) -> List[ProcessInfo]:
        """Get top GPU processes by memory usage."""
        processes = []

        try:
            result = subprocess.run(
                ['nvidia-smi', 'pmon', '-c', '1', '-s', 'um'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return processes

            lines = result.stdout.strip().split('\n')
            # Parse pmon output
            for line in lines:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        pid = int(parts[0])
                        name = parts[1]
                        gpu_id = int(parts[2])
                        memory_mb = int(parts[4]) if parts[4].isdigit() else 0

                        if memory_mb > 0:
                            processes.append(ProcessInfo(
                                pid=pid,
                                name=name,
                                gpu_id=gpu_id,
                                memory_mb=memory_mb
                            ))
                    except (ValueError, IndexError):
                        continue

        except subprocess.TimeoutExpired:
            pass

        # Sort by memory usage and return top N
        processes.sort(key=lambda p: p.memory_mb, reverse=True)
        return processes[:self._top_n]

    def collect(self) -> tuple[MemoryInfo, List[ProcessInfo]]:
        """Collect CPU memory and process information."""
        if not self._initialized:
            raise RuntimeError("CPUMonitor not initialized. Call initialize() first.")

        memory_info = self.get_memory_info()
        gpu_processes = self.get_gpu_processes()

        return memory_info, gpu_processes

"""GPU data collection module using nvidia-smi."""

import subprocess
import threading
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class GPUInfo:
    """Data class for GPU information."""
    gpu_id: int
    name: str
    memory_used: int  # MB
    memory_total: int  # MB
    utilization: int  # %
    temperature: int  # °C
    power: float  # W
    power_limit: float = 0.0  # W
    pcie_bandwidth: float = 0.0  # MB/s (combined, for backward compatibility)
    pcie_tx: float = 0.0  # MB/s (transmit: GPU → CPU)
    pcie_rx: float = 0.0  # MB/s (receive: CPU → GPU)
    offline: bool = False

    @property
    def memory_percent(self) -> float:
        return (self.memory_used / self.memory_total * 100) if self.memory_total > 0 else 0


class GPUMonitor:
    """Monitor GPU status using nvidia-smi."""

    def __init__(self):
        self._gpu_count = 0
        self._gpu_names: List[str] = []
        self._last_pcie_values: Dict[int, tuple] = {}
        self._lock = threading.Lock()
        self._initialized = False

    def _check_nvidia_smi(self) -> bool:
        """Check if nvidia-smi is available."""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=count', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def initialize(self) -> bool:
        """Initialize the GPU monitor and get GPU names."""
        with self._lock:
            if not self._check_nvidia_smi():
                raise RuntimeError("nvidia-smi not found. Please install NVIDIA drivers.")

            try:
                # Get GPU count and names
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    raise RuntimeError("Failed to query GPU information")

                self._gpu_names = [line.strip() for line in result.stdout.strip().split('\n')]
                self._gpu_count = len(self._gpu_names)
                self._initialized = True
                return True

            except subprocess.TimeoutExpired:
                raise RuntimeError("nvidia-smi command timed out")

    @property
    def gpu_count(self) -> int:
        """Return the number of GPUs."""
        return self._gpu_count

    @property
    def gpu_names(self) -> List[str]:
        """Return the list of GPU names."""
        return self._gpu_names.copy()

    def collect(self) -> List[GPUInfo]:
        """Collect current GPU statistics."""
        if not self._initialized:
            raise RuntimeError("GPUMonitor not initialized. Call initialize() first.")

        gpus = []

        try:
            # Query all GPU metrics at once
            result = subprocess.run(
                [
                    'nvidia-smi',
                    '--query-gpu=index,memory.used,memory.total,utilization.gpu,'
                    'temperature.gpu,power.draw,power.limit',
                    '--format=csv,noheader,nounits'
                ],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                # Return offline GPUs if query fails
                return [GPUInfo(gpu_id=i, name=name, memory_used=0, memory_total=0,
                              utilization=0, temperature=0, power=0, offline=True)
                       for i, name in enumerate(self._gpu_names)]

            # Parse output
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 7:
                    gpu_id = int(parts[0])
                    name = self._gpu_names[gpu_id] if gpu_id < len(self._gpu_names) else "Unknown"
                    gpus.append(GPUInfo(
                        gpu_id=gpu_id,
                        name=name,
                        memory_used=int(parts[1]),
                        memory_total=int(parts[2]),
                        utilization=int(parts[3]),
                        temperature=int(parts[4]),
                        power=float(parts[5]),
                        power_limit=float(parts[6])
                    ))

        except subprocess.TimeoutExpired:
            # Return offline GPUs on timeout
            return [GPUInfo(gpu_id=i, name=name, memory_used=0, memory_total=0,
                          utilization=0, temperature=0, power=0, offline=True)
                   for i, name in enumerate(self._gpu_names)]

        return gpus

    def get_pcie_bandwidth(self, gpu_id: int, current_rx: float, current_tx: float,
                          interval: float) -> float:
        """Calculate PCIe bandwidth based on delta."""
        key = gpu_id
        last_rx, last_tx, last_time = self._last_pcie_values.get(key, (current_rx, current_tx, 0))

        bandwidth = 0.0
        if last_time > 0:
            time_delta = interval
            rx_delta = current_rx - last_rx
            tx_delta = current_tx - last_tx
            bandwidth = (rx_delta + tx_delta) / time_delta if time_delta > 0 else 0

        self._last_pcie_values[key] = (current_rx, current_tx, interval)
        return max(0, bandwidth)

"""Optimized NVIDIA data collector using dmon for PCIe."""

import subprocess
import re
from typing import List, Dict
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
    power_limit: float  # W
    graphics_clock: int  # MHz (current)
    graphics_clock_max: int  # MHz (max)
    pcie_tx: float = 0.0  # MB/s
    pcie_rx: float = 0.0  # MB/s
    pcie_bandwidth: float = 0.0  # MB/s
    offline: bool = False

    @property
    def memory_percent(self) -> float:
        return (self.memory_used / self.memory_total * 100) if self.memory_total > 0 else 0


class NvidiaCollector:
    """Fast NVIDIA collector using dmon for PCIe throughput."""

    def __init__(self):
        self._gpu_count = 0
        self._gpu_names: List[str] = []
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the collector."""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("Failed to query GPU")

            self._gpu_names = [line.strip() for line in result.stdout.strip().split('\n')]
            self._gpu_count = len(self._gpu_names)
            self._initialized = True
            return True

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise RuntimeError(f"nvidia-smi error: {e}")

    @property
    def gpu_count(self) -> int:
        return self._gpu_count

    def collect_all(self) -> List['GPUInfo']:
        """Collect all GPU data."""
        if not self._initialized:
            raise RuntimeError("Not initialized")

        try:
            # Fast query for main GPU data
            result = subprocess.run(
                [
                    'nvidia-smi',
                    '--query-gpu=index,memory.used,memory.total,utilization.gpu,'
                    'temperature.gpu,power.draw,power.limit,clocks.current.graphics,'
                    'clocks.max.graphics',
                    '--format=csv,noheader,nounits'
                ],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode != 0:
                return self._get_offline_gpus()

            gpus = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 9:
                    gpu_id = int(parts[0])
                    gpus.append(GPUInfo(
                        gpu_id=gpu_id,
                        name=self._gpu_names[gpu_id] if gpu_id < len(self._gpu_names) else "Unknown",
                        memory_used=int(parts[1]),
                        memory_total=int(parts[2]),
                        utilization=int(parts[3]),
                        temperature=int(parts[4]),
                        power=float(parts[5]),
                        power_limit=float(parts[6]),
                        graphics_clock=int(parts[7]),
                        graphics_clock_max=int(parts[8])
                    ))

            # Get PCIe throughput using dmon (much faster!)
            pcie_data = self._get_pcie_from_dmon()
            for gpu in gpus:
                if gpu.gpu_id in pcie_data:
                    gpu.pcie_tx = pcie_data[gpu.gpu_id]['tx']
                    gpu.pcie_rx = pcie_data[gpu.gpu_id]['rx']
                    gpu.pcie_bandwidth = gpu.pcie_tx + gpu.pcie_rx

            return gpus

        except (subprocess.TimeoutExpired, ValueError, IndexError):
            return self._get_offline_gpus()

    def _get_pcie_from_dmon(self) -> Dict[int, Dict[str, float]]:
        """Get PCIe throughput from nvidia-smi dmon."""
        pcie_data = {}
        try:
            result = subprocess.run(
                ['nvidia-smi', 'dmon', '-c', '1', '-s', 't'],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode != 0:
                return pcie_data

            lines = result.stdout.split('\n')
            for line in lines:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        gpu_id = int(parts[0])
                        rx_mb = float(parts[1])
                        tx_mb = float(parts[2])
                        pcie_data[gpu_id] = {'tx': tx_mb, 'rx': rx_mb}
                    except (ValueError, IndexError):
                        continue

        except subprocess.TimeoutExpired:
            pass

        return pcie_data

    def _get_offline_gpus(self) -> List['GPUInfo']:
        """Return offline GPUs."""
        return [GPUInfo(gpu_id=i, name=name, memory_used=0, memory_total=0,
                       utilization=0, temperature=0, power=0, power_limit=0,
                       graphics_clock=0, graphics_clock_max=0, offline=True)
                for i, name in enumerate(self._gpu_names)]

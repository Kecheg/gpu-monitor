"""PCIe bandwidth monitoring module."""

import subprocess
import re
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class PCIeInfo:
    """Data class for PCIe information."""
    gpu_id: int
    rx_mb: float  # MB/s received
    tx_mb: float  # MB/s transmitted
    bandwidth: float = 0.0  # Total MB/s


class PCIeBandwidthMonitor:
    """Monitor PCIe bandwidth using nvidia-smi -q."""

    # Unit conversion factors
    UNIT_FACTORS = {
        'KB/s': 1 / 1024,      # Convert to MB/s
        'MB/s': 1,             # Already in MB/s
        'GB/s': 1024,          # Convert to MB/s
    }

    def __init__(self, gpu_count: int):
        self._gpu_count = gpu_count
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the PCIe monitor."""
        self._initialized = True
        return True

    def _parse_throughput_value(self, value_str: str) -> float:
        """Parse throughput value like '390 KB/s' to MB/s."""
        value_str = value_str.strip()

        # Match pattern: number + space + unit
        match = re.match(r'([\d.]+)\s+(\S+)', value_str)
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            factor = self.UNIT_FACTORS.get(unit, 1)
            return value * factor

        return 0.0

    def _read_nvidia_smi_throughput(self) -> Dict[int, PCIeInfo]:
        """Read PCIe throughput from nvidia-smi -q."""
        pcie_data = {}

        try:
            result = subprocess.run(
                ['nvidia-smi', '-q'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return pcie_data

            lines = result.stdout.split('\n')
            gpu_id = None
            tx_throughput = None
            rx_throughput = None

            for line in lines:
                # Detect GPU boundary
                if line.strip().startswith('GPU ') and ':' in line:
                    # Save previous GPU data if exists
                    if gpu_id is not None and tx_throughput is not None and rx_throughput is not None:
                        total_mb = tx_throughput + rx_throughput
                        pcie_data[gpu_id] = PCIeInfo(
                            gpu_id=gpu_id,
                            tx_mb=tx_throughput,
                            rx_mb=rx_throughput,
                            bandwidth=total_mb
                        )

                    # Extract new GPU ID from line like "GPU 0000:18:00.0"
                    match = re.search(r'GPU\s+[\da-fA-F:\.]+', line)
                    if match:
                        gpu_id = len(pcie_data)  # Assign sequential ID
                        tx_throughput = None
                        rx_throughput = None

                # Parse Tx Throughput
                elif 'Tx Throughput' in line and ':' in line:
                    value_part = line.split(':', 1)[1].strip()
                    tx_throughput = self._parse_throughput_value(value_part)

                # Parse Rx Throughput
                elif 'Rx Throughput' in line and ':' in line:
                    value_part = line.split(':', 1)[1].strip()
                    rx_throughput = self._parse_throughput_value(value_part)

            # Save last GPU data
            if gpu_id is not None and tx_throughput is not None and rx_throughput is not None:
                total_mb = tx_throughput + rx_throughput
                pcie_data[gpu_id] = PCIeInfo(
                    gpu_id=gpu_id,
                    tx_mb=tx_throughput,
                    rx_mb=rx_throughput,
                    bandwidth=total_mb
                )

        except subprocess.TimeoutExpired:
            pass

        return pcie_data

    def collect(self, interval: float = 2.0) -> Dict[int, PCIeInfo]:
        """Collect PCIe bandwidth data."""
        if not self._initialized:
            raise RuntimeError("PCIeBandwidthMonitor not initialized. Call initialize() first.")

        # nvidia-smi -q provides instantaneous throughput, no delta calculation needed
        return self._read_nvidia_smi_throughput()

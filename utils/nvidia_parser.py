"""NVIDIA-smi output parser utility."""

import re
from typing import Dict, List, Optional, Tuple


class NvidiaParser:
    """Parse nvidia-smi output in various formats."""

    @staticmethod
    def parse_query_gpu(output: str) -> List[Dict[str, any]]:
        """Parse nvidia-smi --query-gpu CSV output."""
        results = []
        for line in output.strip().split('\n'):
            if not line:
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 6:
                try:
                    results.append({
                        'index': int(parts[0]),
                        'memory_used': int(parts[1]),
                        'memory_total': int(parts[2]),
                        'utilization': int(parts[3]),
                        'temperature': int(parts[4]),
                        'power': float(parts[5])
                    })
                except (ValueError, IndexError):
                    continue
        return results

    @staticmethod
    def parse_dmon(output: str) -> Dict[int, Dict[str, float]]:
        """Parse nvidia-smi dmon output."""
        results = {}
        lines = output.strip().split('\n')

        for line in lines:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 11:
                try:
                    gpu_id = int(parts[0])
                    results[gpu_id] = {
                        'pci_rx': float(parts[9]),
                        'pci_tx': float(parts[10])
                    }
                except (ValueError, IndexError):
                    continue

        return results

    @staticmethod
    def parse_pmon(output: str) -> List[Dict[str, any]]:
        """Parse nvidia-smi pmon output."""
        results = []
        lines = output.strip().split('\n')

        for line in lines:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 5:
                try:
                    results.append({
                        'pid': int(parts[0]),
                        'name': parts[1],
                        'gpu_id': int(parts[2]),
                        'memory_mb': int(parts[4]) if parts[4].isdigit() else 0
                    })
                except (ValueError, IndexError):
                    continue

        return results

    @staticmethod
    def get_gpu_count(output: str) -> int:
        """Extract GPU count from nvidia-smi output."""
        match = re.search(r'(\d+)\s+GPU', output)
        if match:
            return int(match.group(1))
        return 0

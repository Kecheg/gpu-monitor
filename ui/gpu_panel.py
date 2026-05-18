"""GPU panel UI component for displaying GPU information."""

import curses
from typing import List, Optional
try:
    from ..core.nvidia_collector import GPUInfo
    from ..core.alert_manager import AlertManager, AlertLevel
except ImportError:
    from core.nvidia_collector import GPUInfo
    from core.alert_manager import AlertManager, AlertLevel


class GPUPanel:
    """Panel for displaying GPU information in curses UI."""

    def __init__(self, alert_manager: AlertManager, width: int = 18, height: int = 11):
        self._alert_manager = alert_manager
        self._width = width
        self._height = height
        self._selected = False

        # Color pairs
        self.COLOR_NORMAL = 0
        self.COLOR_WARNING = 1
        self.COLOR_DANGER = 2
        self.COLOR_SELECTED = 3

    def set_selected(self, selected: bool):
        """Set selection state."""
        self._selected = selected

    def set_width(self, width: int):
        """Set panel width dynamically."""
        self._width = width

    def _format_memory(self, used: int, total: int) -> str:
        """Format memory display."""
        if total >= 1024:
            return f"{used // 1024}/{total // 1024}GB"
        return f"{used}/{total}MB"

    def _format_bandwidth(self, bandwidth: float) -> str:
        """Format bandwidth display."""
        if bandwidth >= 1024:
            return f"{bandwidth / 1024:.1f}GB/s"
        return f"{bandwidth:.0f}MB/s"

    def _get_color_level(self, gpu: GPUInfo) -> AlertLevel:
        """Get alert level for GPU."""
        if gpu.offline:
            return AlertLevel.DANGER
        return self._alert_manager.get_overall_gpu_level(
            gpu.utilization, gpu.memory_percent, gpu.temperature
        )

    def _get_color_pair(self, level: AlertLevel) -> int:
        """Get curses color pair for alert level."""
        if self._selected:
            return self.COLOR_SELECTED
        return self._alert_manager.get_color_pair(level)

    def _safe_addstr(self, win, y: int, x: int, text: str, color: int = 0):
        """Safely add string to window with boundary checking."""
        try:
            max_y, max_x = win.getmaxyx()
            if y >= max_y or x >= max_x:
                return
            safe_text = text[:max_x - x - 1] if x + len(text) > max_x else text
            win.addstr(y, x, safe_text, color)
        except (curses.error, ValueError):
            pass

    def draw(self, win, y: int, x: int, gpu: GPUInfo):
        """Draw GPU panel at specified position."""
        level = self._get_color_level(gpu)
        color = self._get_color_pair(level)

        # Clear area
        for dy in range(self._height):
            self._safe_addstr(win, y + dy, x, " " * self._width)

        # GPU header
        header = f"GPU{gpu.gpu_id}" + " " * (self._width - 5)
        self._safe_addstr(win, y, x, header[:self._width])

        # GPU name (truncated)
        name = gpu.name[:self._width]
        if len(name) < self._width:
            name += " " * (self._width - len(name))
        self._safe_addstr(win, y+ 1, x, name[:self._width])

        # Memory
        if gpu.offline:
            mem_line = "Mem: Offline"
        else:
            mem_line = f"Mem: {self._format_memory(gpu.memory_used, gpu.memory_total)}"
        if len(mem_line) < self._width:
            mem_line += " " * (self._width - len(mem_line))
        self._safe_addstr(win, y+ 2, x, mem_line[:self._width])

        # Utilization
        if gpu.offline:
            util_line = "Util: N/A"
        else:
            util_line = f"Util: {gpu.utilization}%"
        if len(util_line) < self._width:
            util_line += " " * (self._width - len(util_line))
        self._safe_addstr(win, y+ 3, x, util_line[:self._width])

        # Temperature
        if gpu.offline:
            temp_line = "Temp: N/A"
        else:
            temp_line = f"Temp: {gpu.temperature}°C"
        if len(temp_line) < self._width:
            temp_line += " " * (self._width - len(temp_line))
        self._safe_addstr(win, y+ 4, x, temp_line[:self._width])

        # Power: current/limit
        if gpu.offline:
            power_line = "Power: N/A"
        else:
            if gpu.power_limit > 0:
                power_pct = int(gpu.power / gpu.power_limit * 100)
                power_line = f"Pwr: {gpu.power:.0f}/{gpu.power_limit:.0f}W ({power_pct}%)"
            else:
                power_line = f"Pwr: {gpu.power:.0f}W"
        if len(power_line) < self._width:
            power_line += " " * (self._width - len(power_line))
        self._safe_addstr(win, y+ 5, x, power_line[:self._width])

        # Graphics Clock: current/max
        if gpu.offline:
            clk_line = "Clock: N/A"
        else:
            if gpu.graphics_clock_max > 0:
                clk_pct = int(gpu.graphics_clock / gpu.graphics_clock_max * 100) if gpu.graphics_clock_max > 0 else 0
                clk_line = f"Clk: {gpu.graphics_clock}/{gpu.graphics_clock_max}MHz ({clk_pct}%)"
            else:
                clk_line = f"Clk: {gpu.graphics_clock}MHz"
        if len(clk_line) < self._width:
            clk_line += " " * (self._width - len(clk_line))
        self._safe_addstr(win, y+ 6, x, clk_line[:self._width])

        # PCIe bandwidth - TX, RX, Total
        if gpu.offline:
            pcie_tx_line = "PCIe-TX: N/A"
            pcie_rx_line = "PCIe-RX: N/A"
            pcie_total_line = "PCIe-Total: N/A"
        else:
            pcie_tx_line = f"PCIe-TX: {self._format_bandwidth(gpu.pcie_tx)}"
            pcie_rx_line = f"PCIe-RX: {self._format_bandwidth(gpu.pcie_rx)}"
            pcie_total_line = f"PCIe-Total: {self._format_bandwidth(gpu.pcie_bandwidth)}"

        if len(pcie_tx_line) < self._width:
            pcie_tx_line += " " * (self._width - len(pcie_tx_line))
        if len(pcie_rx_line) < self._width:
            pcie_rx_line += " " * (self._width - len(pcie_rx_line))
        if len(pcie_total_line) < self._width:
            pcie_total_line += " " * (self._width - len(pcie_total_line))

        self._safe_addstr(win, y+ 7, x, pcie_tx_line[:self._width])
        self._safe_addstr(win, y+ 8, x, pcie_rx_line[:self._width])
        self._safe_addstr(win, y+ 9, x, pcie_total_line[:self._width])

    def get_width(self) -> int:
        """Return panel width."""
        return self._width

    def get_height(self) -> int:
        """Return panel height."""
        return self._height

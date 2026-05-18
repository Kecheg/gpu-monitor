"""GPU panel V2 UI component with progress bars for visual metrics."""

import curses
from typing import List, Optional
try:
    from ..core.nvidia_collector import GPUInfo
    from ..core.alert_manager import AlertManager, AlertLevel
except ImportError:
    from core.nvidia_collector import GPUInfo
    from core.alert_manager import AlertManager, AlertLevel


class GPUPanelV2:
    """V2 Panel for displaying GPU information with progress bars."""

    # Progress bar characters for different widths
    _BLOCK_CHARS = {
        'full': '█',
        'three_quarter': '▓',
        'half': '▒',
        'quarter': '░',
        'empty': ' '
    }

    def __init__(self, alert_manager: AlertManager, width: int = 28, height: int = 13):
        self._alert_manager = alert_manager
        self._width = width
        self._height = height
        self._selected = False

        # PCIe Gen4 x16 theoretical max: ~32 GB/s per direction
        self._PCIE_MAX_GB = 32.0  # GB/s

        # Color pairs
        self.COLOR_NORMAL = 0
        self.COLOR_WARNING = 1
        self.COLOR_DANGER = 2
        self.COLOR_SELECTED = 3
        self.COLOR_PROGRESS_OK = 5
        self.COLOR_PROGRESS_WARN = 6
        self.COLOR_PROGRESS_DANGER = 7

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

    def _get_progress_color(self, percent: float) -> int:
        """Get progress bar color based on percentage."""
        if percent >= 95:
            return self.COLOR_PROGRESS_DANGER
        elif percent >= 80:
            return self.COLOR_PROGRESS_WARN
        return self.COLOR_PROGRESS_OK

    def _draw_progress_bar(self, win, y: int, x: int, width: int, percent: float,
                           label: str, value_str: str, color_pair: int, show_pct: bool = True):
        """Draw a horizontal progress bar.

        Args:
            win: curses window
            y, x: position
            width: bar width in characters
            percent: 0-100
            label: text label to show before bar
            value_str: value text to show after bar
            color_pair: color pair for the filled portion
            show_pct: whether to show percentage after value
        """
        # Get terminal dimensions for boundary checking
        try:
            max_y, max_x = win.getmaxyx()
        except:
            return  # Can't get dimensions, skip drawing

        # Check if starting position is valid
        if y >= max_y or x >= max_x:
            return

        # Label + value space calculation
        label_len = len(label)
        pct_str = f" ({percent:.0f}%)" if show_pct else ""
        value_with_pct = value_str + pct_str
        value_len = len(value_with_pct)

        # Available width for progress bar (ensure it fits)
        available_width = self._width - label_len - value_len - 2
        bar_width = max(3, min(available_width, max_x - x - label_len - value_len - 1))

        # Calculate filled characters
        filled = int(bar_width * percent / 100)

        # Draw label with truncation if needed
        try:
            safe_label = label[:max_x - x - 1] if x + len(label) > max_x else label
            win.addstr(y, x, safe_label)
        except curses.error:
            pass

        # Draw progress bar
        bar_x = x + len(label)
        if bar_x + bar_width > max_x:
            bar_width = max(0, max_x - bar_x)

        for i in range(bar_width):
            draw_x = bar_x + i
            if draw_x >= max_x:
                break
            if i < filled:
                # Filled portion - use color
                try:
                    win.addstr(y, draw_x, self._BLOCK_CHARS['full'],
                              curses.color_pair(color_pair) if color_pair > 0 else 0)
                except curses.error:
                    pass
            else:
                # Empty portion
                try:
                    win.addstr(y, draw_x, self._BLOCK_CHARS['empty'])
                except curses.error:
                    pass

        # Draw value with percentage (truncated if needed)
        value_x = bar_x + bar_width + 1
        if value_x < max_x:
            try:
                safe_value = value_with_pct[:max_x - value_x - 1]
                win.addstr(y, value_x, safe_value)
            except curses.error:
                pass

    def _draw_mini_progress(self, win, y: int, x: int, bar_width: int,
                            percent: float, color_pair: int):
        """Draw a mini progress bar (just the bar, no labels).

        Args:
            win: curses window
            y, x: position
            bar_width: bar width
            percent: 0-100
            color_pair: color for filled portion
        """
        filled = int(bar_width * percent / 100)
        for i in range(bar_width):
            if i < filled:
                try:
                    win.addstr(y, x + i, "=", curses.color_pair(color_pair) if color_pair > 0 else 0)
                except curses.error:
                    pass
            else:
                try:
                    win.addstr(y, x + i, "-")
                except curses.error:
                    pass

    def draw(self, win, y: int, x: int, gpu: GPUInfo):
        """Draw GPU panel at specified position."""
        if gpu.offline:
            self._draw_offline(win, y, x)
            return

        level = self._get_color_level(gpu)
        base_color = self._get_color_pair(level)

        # Get terminal dimensions for boundary checking
        try:
            max_y, max_x = win.getmaxyx()
        except:
            return  # Can't get dimensions, skip drawing

        # Check if panel fits on screen
        if y + self._height > max_y or x + self._width > max_x:
            return  # Panel won't fit, skip drawing

        # Clear area with boundary check
        for dy in range(min(self._height, max_y - y)):
            clear_width = min(self._width, max_x - x)
            try:
                win.addstr(y + dy, x, " " * clear_width)
            except curses.error:
                pass

        # Header line (with truncation)
        header = f"GPU{gpu.gpu_id}"
        if len(gpu.name) > 0:
            short_name = gpu.name[:10].replace(' ', '')
            if len(short_name) > 0:
                header += f" [{short_name}]"
        safe_width = min(len(header), max_x - x - 1)
        header = header[:safe_width].ljust(self._width)[:self._width]
        try:
            win.addstr(y, x, header[:max_x - x], base_color)
        except curses.error:
            pass

        # GPU name (full, truncated)
        name_line = gpu.name[:self._width]
        if len(name_line) < self._width:
            name_line += " " * (self._width - len(name_line))
        try:
            win.addstr(y + 1, x, name_line[:max_x - x - 1])
        except curses.error:
            pass

        # Progress bars for metrics with clear limits

        # 1. Memory Progress Bar
        mem_pct = gpu.memory_percent
        mem_label = "Mem:"
        mem_used = gpu.memory_used // 1024 if gpu.memory_total >= 1024 else gpu.memory_used
        mem_total = gpu.memory_total // 1024 if gpu.memory_total >= 1024 else gpu.memory_total
        mem_unit = "GB" if gpu.memory_total >= 1024 else "MB"
        mem_str = f"{mem_used}|{mem_total}{mem_unit}"
        mem_color = self._get_progress_color(mem_pct)
        self._draw_progress_bar(win, y + 3, x, self._width, mem_pct,
                               mem_label, mem_str, mem_color)

        # 2. Utilization Progress Bar
        util_pct = gpu.utilization
        util_label = "Util:"
        util_str = f"{util_pct}%|100%"
        util_color = self._get_progress_color(util_pct)
        self._draw_progress_bar(win, y + 4, x, self._width, util_pct,
                               util_label, util_str, util_color, show_pct=False)

        # 3. Temperature (with progress bar relative to thermal limit)
        temp_limit = 85  # °C thermal reference
        temp_pct = min(100, (gpu.temperature / temp_limit) * 100)
        temp_label = "Temp:"
        temp_str = f"{gpu.temperature}°C|{temp_limit}°C"
        temp_color = self._get_progress_color(temp_pct)
        self._draw_progress_bar(win, y + 5, x, self._width, temp_pct,
                               temp_label, temp_str, temp_color)

        # 4. Power (with progress bar relative to limit)
        if gpu.power_limit > 0:
            power_pct = (gpu.power / gpu.power_limit) * 100
            power_limit_val = gpu.power_limit
        else:
            power_pct = min(100, (gpu.power / 350) * 100)  # 350W as reference
            power_limit_val = 350
        power_label = "Pwr:"
        power_str = f"{gpu.power:.0f}W|{power_limit_val:.0f}W"
        power_color = self._get_progress_color(power_pct)
        self._draw_progress_bar(win, y + 6, x, self._width, power_pct,
                               power_label, power_str, power_color)

        # 5. Clock Speed (with progress bar relative to max)
        if gpu.graphics_clock_max > 0:
            clk_pct = (gpu.graphics_clock / gpu.graphics_clock_max) * 100
            clk_max = gpu.graphics_clock_max
        else:
            clk_pct = min(100, (gpu.graphics_clock / 2000) * 100)  # 2GHz as reference
            clk_max = 2000
        clk_label = "Clk:"
        clk_str = f"{gpu.graphics_clock}|{clk_max}MHz"
        clk_color = self._get_progress_color(clk_pct)
        self._draw_progress_bar(win, y + 7, x, self._width, clk_pct,
                               clk_label, clk_str, clk_color)

        # PCIe Bandwidth Section
        # Convert to GB/s for display, use MB if < 1GB
        pcie_tx_gb = gpu.pcie_tx / 1024
        pcie_rx_gb = gpu.pcie_rx / 1024
        pcie_total_gb = pcie_tx_gb + pcie_rx_gb

        # Format PCIe bandwidth - use MB if < 1GB, always show limit with |
        def format_pcie_with_limit(gb_val, limit_gb):
            if gb_val >= 1:
                return f"{gb_val:.1f}|{limit_gb:.0f}GB/s"
            return f"{gb_val * 1024:.0f}MB/s|{limit_gb:.0f}GB/s"

        # Calculate percentages relative to Gen4 x16 theoretical max (32GB/s)
        pcie_tx_pct = min(100, (pcie_tx_gb / self._PCIE_MAX_GB) * 100)
        pcie_rx_pct = min(100, (pcie_rx_gb / self._PCIE_MAX_GB) * 100)

        # PCIe TX bar
        tx_label = "PCIe-TX:"
        tx_str = format_pcie_with_limit(pcie_tx_gb, self._PCIE_MAX_GB)
        tx_color = self._get_progress_color(pcie_tx_pct)
        self._draw_progress_bar(win, y + 9, x, self._width, pcie_tx_pct,
                               tx_label, tx_str, tx_color)

        # PCIe RX bar
        rx_label = "PCIe-RX:"
        rx_str = format_pcie_with_limit(pcie_rx_gb, self._PCIE_MAX_GB)
        rx_color = self._get_progress_color(pcie_rx_pct)
        self._draw_progress_bar(win, y + 10, x, self._width, pcie_rx_pct,
                               rx_label, rx_str, rx_color)

        # Total PCIe (limit is 64GB/s = 32GB/s * 2)
        total_pct = min(100, (pcie_total_gb / (self._PCIE_MAX_GB * 2)) * 100)
        total_label = "PCIe-Total:"
        total_limit = self._PCIE_MAX_GB * 2
        if pcie_total_gb >= 1:
            total_str = f"{pcie_total_gb:.1f}|{total_limit:.0f}GB/s"
        else:
            total_str = f"{pcie_total_gb * 1024:.0f}MB/s|{total_limit:.0f}GB/s"
        total_color = self._get_progress_color(total_pct)
        self._draw_progress_bar(win, y + 11, x, self._width, total_pct,
                               total_label, total_str, total_color)

    def _draw_offline(self, win, y: int, x: int):
        """Draw offline GPU panel."""
        for dy in range(self._height):
            try:
                win.addstr(y + dy, x, " " * self._width)
            except curses.error:
                pass

        header = f"GPU - OFFLINE".ljust(self._width)[:self._width]
        win.addstr(y, x, header, curses.color_pair(self.COLOR_DANGER) if self._has_colors() else 0)

        offline_msg = "GPU not responding".center(self._width)
        win.addstr(y + self._height // 2, x, offline_msg)

    def _has_colors(self) -> bool:
        """Check if colors are available."""
        return hasattr(self._alert_manager, '_has_colors')

    def get_width(self) -> int:
        """Return panel width."""
        return self._width

    def get_height(self) -> int:
        """Return panel height."""
        return self._height

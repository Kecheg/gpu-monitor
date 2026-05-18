"""Main curses window for GPU monitor UI V2 with progress bars."""

import curses
import curses.ascii
from typing import List, Optional
from datetime import datetime

from .gpu_panel_v2 import GPUPanelV2
try:
    from ..core.nvidia_collector import GPUInfo
    from ..core.cpu_monitor import MemoryInfo, ProcessInfo
    from ..core.alert_manager import AlertManager, AlertLevel
except ImportError:
    from core.nvidia_collector import GPUInfo
    from core.cpu_monitor import MemoryInfo, ProcessInfo
    from core.alert_manager import AlertManager, AlertLevel


class UIMainV2:
    """V2 Main curses UI window with progress bar visualization."""

    def __init__(self, alert_manager: AlertManager):
        self._alert_manager = alert_manager
        self._stdscr: Optional[curses.window] = None
        self._panels: List[GPUPanelV2] = []
        self._selected_gpu = 0
        self._refresh_rate = 2
        self._log_file = ""
        self._running = False

        # Color definitions
        self.COLOR_DEFAULT = 0
        self.COLOR_WARNING = 1
        self.COLOR_DANGER = 2
        self.COLOR_SELECTED = 3
        self.COLOR_HEADER = 4
        self.COLOR_PROGRESS_OK = 5
        self.COLOR_PROGRESS_WARN = 6
        self.COLOR_PROGRESS_DANGER = 7

        # Layout
        self._panel_width = 32
        self._panel_height = 13

    def _init_colors(self):
        """Initialize curses color pairs including progress bar colors."""
        curses.init_pair(self.COLOR_WARNING, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(self.COLOR_DANGER, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(self.COLOR_SELECTED, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(self.COLOR_HEADER, curses.COLOR_CYAN, curses.COLOR_BLACK)
        # Progress bar colors
        curses.init_pair(self.COLOR_PROGRESS_OK, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(self.COLOR_PROGRESS_WARN, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(self.COLOR_PROGRESS_DANGER, curses.COLOR_RED, curses.COLOR_BLACK)
        self._has_colors = True

    def _color(self, color_id: int) -> int:
        """Get color pair, returning 0 if colors not available."""
        if hasattr(self, '_has_colors') and self._has_colors and color_id > 0:
            return curses.color_pair(color_id)
        return 0

    def _calculate_layout(self, gpu_count: int):
        """Calculate panel dimensions based on terminal size."""
        if not self._stdscr:
            return 32, 13, 4

        height, width = self._stdscr.getmaxyx()

        # Reserve space for header (2 lines) and bottom section
        available_height = height - 10
        if available_height < 12:
            available_height = 12

        # V2 panels are taller due to progress bars
        panel_height = min(15, available_height - 2)
        if panel_height < 13:
            panel_height = 13

        # Calculate panel width - V2 needs more width for progress bars
        panels_per_row = 4
        panel_width = (width - 10) // panels_per_row
        if panel_width < 28:
            panel_width = 28
        if panel_width > 40:
            panel_width = 40

        return panel_width, panel_height, panels_per_row

    def _create_panels(self, gpu_count: int):
        """Create GPU panels with dynamic sizing."""
        panel_width, panel_height, _ = self._calculate_layout(gpu_count)
        self._panel_width = panel_width
        self._panel_height = panel_height
        self._panels = [GPUPanelV2(self._alert_manager, panel_width, panel_height)
                       for _ in range(gpu_count)]

    def _draw_header(self):
        """Draw header line."""
        if not self._stdscr:
            return

        height, width = self._stdscr.getmaxyx()
        header = f"GPU Monitor V2 [Progress Bars] - Refresh: {self._refresh_rate}s"

        if self._log_file:
            log_part = f" | Logs: {self._log_file}"
            if len(header) + len(log_part) < width - 2:
                header += log_part

        # Clear header line
        self._stdscr.addstr(0, 0, " " * width)
        self._stdscr.addstr(0, 0, header, self._color(self.COLOR_HEADER))

    def _draw_separator(self, y: int):
        """Draw horizontal separator line."""
        if not self._stdscr:
            return
        height, width = self._stdscr.getmaxyx()
        self._stdscr.addstr(y, 0, "─" * width)

    def _draw_gpu_section(self, gpus: List[GPUInfo], start_y: int) -> int:
        """Draw GPU panels section. Returns next y position."""
        if not self._stdscr:
            return start_y

        # Calculate layout dynamically
        panel_width, panel_height, panels_per_row = self._calculate_layout(len(gpus))

        # Update panel dimensions
        self._panel_width = panel_width
        self._panel_height = panel_height

        # Update panel selection states
        for i, panel in enumerate(self._panels):
            panel.set_selected(i == self._selected_gpu)
            panel.set_width(panel_width)

        # Draw panels
        row = 0
        col = 0
        for i, gpu in enumerate(gpus):
            if i >= len(self._panels):
                break

            panel_x = 1 + col * (panel_width + 1)
            panel_y = start_y + row * (panel_height + 1)

            self._panels[i].draw(self._stdscr, panel_y, panel_x, gpu)

            col += 1
            if col >= panels_per_row:
                col = 0
                row += 1

        return start_y + (row + 1) * (self._panel_height + 1)

    def _draw_cpu_section(self, memory: MemoryInfo, start_y: int) -> int:
        """Draw CPU/memory section with progress bar. Returns next y position."""
        if not self._stdscr:
            return start_y

        height, width = self._stdscr.getmaxyx()

        # Section label
        self._stdscr.addstr(start_y, 1, "CPU & Memory Info",
                           self._color(self.COLOR_HEADER))

        # Draw memory progress bar
        mem_pct = memory.percent
        bar_width = min(50, width - 30)
        filled = int(bar_width * mem_pct / 100)

        mem_line = f"    Memory: {memory.used_mb // 1024:.1f}GB / {memory.total_mb // 1024:.0f}GB ({mem_pct:.1f}%)"
        self._stdscr.addstr(start_y + 1, 1, mem_line)

        # Draw bar
        bar_x = 15
        bar_y = start_y + 2
        color = self._get_progress_color(mem_pct)
        for i in range(bar_width):
            if i < filled:
                try:
                    self._stdscr.addch(bar_y, bar_x + i, curses.ACS_CKBOARD,
                                      curses.color_pair(color) if color > 0 else 0)
                except curses.error:
                    pass
            else:
                try:
                    self._stdscr.addch(bar_y, bar_x + i, curses.ACS_BOARD,
                                      curses.color_pair(color) if color > 0 else 0)
                except curses.error:
                    pass

        return start_y + 4

    def _get_progress_color(self, percent: float) -> int:
        """Get progress bar color based on percentage."""
        if percent >= 95:
            return self.COLOR_PROGRESS_DANGER
        elif percent >= 80:
            return self.COLOR_PROGRESS_WARN
        return self.COLOR_PROGRESS_OK

    def _draw_process_section(self, processes: List[ProcessInfo], start_y: int):
        """Draw top processes section."""
        if not self._stdscr:
            return

        height, width = self._stdscr.getmaxyx()

        # Section header
        self._stdscr.addstr(start_y, 1, "Top GPU Processes:",
                           self._color(self.COLOR_HEADER))

        # Table header
        self._stdscr.addstr(start_y + 1, 1, "PID    │ Process Name    │ GPU │ Memory (MB)")

        # Process rows
        for i, proc in enumerate(processes[:5]):
            row = start_y + 2 + i
            if row >= height - 1:
                break

            pid_str = f"{proc.pid:<6}"
            name_str = proc.name[:15].ljust(15)
            gpu_str = f"{proc.gpu_id:<4}"
            mem_str = f"{proc.memory_mb:<10}"

            line = f"{pid_str} │ {name_str} │ {gpu_str} │ {mem_str}"
            self._stdscr.addstr(row, 1, line)

    def refresh(self, gpus: List[GPUInfo], memory: MemoryInfo, processes: List[ProcessInfo]):
        """Refresh the UI with new data."""
        if not self._stdscr:
            return

        self._stdscr.clear()
        height, width = self._stdscr.getmaxyx()

        # Draw header
        self._draw_header()

        # Draw separator
        self._draw_separator(1)

        # Draw GPU section
        y = self._draw_gpu_section(gpus, 2)

        # Draw separator if space permits
        if y < height - 8:
            self._draw_separator(y)
            y += 1

            # Draw CPU section
            y = self._draw_cpu_section(memory, y)

            # Draw separator if space permits
            if y < height - 8:
                self._draw_separator(y)
                y += 1

                # Draw processes section
                self._draw_process_section(processes, y)

        self._stdscr.refresh()

    def handle_input(self) -> Optional[str]:
        """Handle keyboard input. Returns action string or None."""
        if not self._stdscr:
            return None

        key = self._stdscr.getch()

        if key == curses.ERR:
            return None

        # Quit
        if key in (ord('q'), curses.ascii.ESC):
            return "quit"

        # Direction keys for GPU selection
        elif key == curses.KEY_RIGHT:
            self._selected_gpu = min(self._selected_gpu + 1, len(self._panels) - 1)
        elif key == curses.KEY_LEFT:
            self._selected_gpu = max(self._selected_gpu - 1, 0)

        # Manual refresh
        elif key == ord('r'):
            return "refresh"

        # Adjust refresh rate
        elif key == ord('+') or key == ord('='):
            self._refresh_rate = min(10, self._refresh_rate + 1)
        elif key == ord('-'):
            self._refresh_rate = max(1, self._refresh_rate - 1)

        return None

    def initialize(self, gpu_count: int, log_file: str = "", refresh_rate: int = 2):
        """Initialize the curses UI."""
        self._stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self._stdscr.keypad(True)
        self._stdscr.nodelay(True)

        # Initialize colors
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            self._init_colors()

        self._create_panels(gpu_count)
        self._log_file = log_file
        self._refresh_rate = refresh_rate

    def cleanup(self):
        """Clean up curses resources."""
        if self._stdscr:
            curses.nocbreak()
            self._stdscr.keypad(False)
            curses.echo()
            curses.endwin()
            self._stdscr = None

    def set_refresh_rate(self, rate: int):
        """Set refresh rate display."""
        self._refresh_rate = rate

    def get_refresh_rate(self) -> int:
        """Get current refresh rate."""
        return self._refresh_rate

    def set_log_file(self, log_file: str):
        """Set log file path for display."""
        self._log_file = log_file

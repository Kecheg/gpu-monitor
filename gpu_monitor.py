#!/usr/bin/env python3
"""GPU Monitor - Real-time GPU monitoring tool.

A terminal-based GPU monitoring tool for NVIDIA GPUs with features similar to htop.
"""

import argparse
import sys
import time
import signal
from datetime import datetime
from pathlib import Path

from core import NvidiaCollector, CPUMonitor, AlertManager
from core.alert_manager import AlertThresholds
from ui import UIMain
from ui.main_window_v2 import UIMainV2
from utils import Config, Logger, load_config, save_default_config


class GPUMonitorApp:
    """Main application class for GPU monitoring."""

    def __init__(self, config: Config, ui_version: str = "v1"):
        self._config = config
        self._ui_version = ui_version
        self._nvidia_collector = NvidiaCollector()
        self._pcie_monitor: PCIeBandwidthMonitor = None
        self._cpu_monitor = CPUMonitor(top_n=5)
        self._logger = Logger(config.log_dir, config.log_retention_days)
        self._ui = None

        # Create alert manager with config thresholds
        thresholds = AlertThresholds(
            gpu_util_warning=config.alerts.gpu_util_warning,
            gpu_util_danger=config.alerts.gpu_util_danger,
            gpu_mem_warning=config.alerts.gpu_mem_warning,
            gpu_mem_danger=config.alerts.gpu_mem_danger,
            gpu_temp_warning=config.alerts.gpu_temp_warning,
            gpu_temp_danger=config.alerts.gpu_temp_danger,
            cpu_mem_warning=config.alerts.cpu_mem_warning,
            cpu_mem_danger=config.alerts.cpu_mem_danger
        )
        self._alert_manager = AlertManager(thresholds)

        self._running = False

    def _initialize_components(self):
        """Initialize all monitoring components."""
        # Initialize unified NVIDIA collector
        self._nvidia_collector.initialize()

        # Initialize CPU monitor
        self._cpu_monitor.initialize()

        # Initialize logger
        if self._config.log_enabled:
            self._logger.initialize()

    def _get_log_file_display(self) -> str:
        """Get log file path for display."""
        if not self._config.log_enabled:
            return ""
        return str(self._logger._get_log_path(datetime.now()))

    def run(self):
        """Run the main monitoring loop."""
        self._initialize_components()

        # Initialize UI based on version
        if self._ui_version == "v2":
            self._ui = UIMainV2(self._alert_manager)
        else:
            self._ui = UIMain(self._alert_manager)
        try:
            self._ui.initialize(
                self._nvidia_collector.gpu_count,
                self._get_log_file_display(),
                self._config.refresh_rate
            )
        except Exception as e:
            print(f"Failed to initialize UI: {e}")
            return 1

        self._running = True

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        last_refresh = time.time()
        last_log = time.time()

        try:
            while self._running:
                current_time = time.time()

                # Handle user input
                action = self._ui.handle_input()
                if action == "quit":
                    break
                elif action == "refresh":
                    last_refresh = 0

                # Get current refresh rate (may be adjusted by +/- keys)
                refresh_rate = self._ui.get_refresh_rate()

                # Refresh data at configured interval
                if current_time - last_refresh >= refresh_rate:
                    last_refresh = current_time

                    # Collect all NVIDIA data in single call
                    gpus = self._nvidia_collector.collect_all()

                    # Collect CPU data
                    memory, processes = self._cpu_monitor.collect()

                    # Update UI
                    self._ui.refresh(gpus, memory, processes)

                    # Log data
                    if self._config.log_enabled and current_time - last_log >= refresh_rate:
                        last_log = current_time
                        self._logger.log_gpu_data(gpus, memory, processes)

                # Small sleep to prevent CPU spin
                time.sleep(0.05)

        except Exception as e:
            self._ui.cleanup()
            print(f"Error: {e}")
            return 1

        self._ui.cleanup()

        if self._config.log_enabled:
            self._logger.close()

        return 0

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self._running = False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="GPU Monitor - Real-time GPU monitoring tool"
    )

    parser.add_argument(
        '-r', '--refresh-rate',
        type=int,
        metavar='SECONDS',
        help='Refresh interval in seconds [1-10], default: 2'
    )

    parser.add_argument(
        '-c', '--config',
        metavar='FILE',
        help='Path to configuration file'
    )

    parser.add_argument(
        '-l', '--log-dir',
        metavar='DIR',
        help='Log directory path'
    )

    parser.add_argument(
        '-d', '--log-retention',
        type=int,
        metavar='DAYS',
        help='Log retention days, default: 7'
    )

    parser.add_argument(
        '--no-log',
        action='store_true',
        help='Disable logging'
    )

    parser.add_argument(
        '--gpu-util-warning',
        type=int,
        metavar='INT',
        help='GPU utilization warning threshold %%'
    )

    parser.add_argument(
        '--gpu-util-danger',
        type=int,
        metavar='INT',
        help='GPU utilization danger threshold %%'
    )

    parser.add_argument(
        '--gpu-mem-warning',
        type=int,
        metavar='INT',
        help='GPU memory warning threshold %%'
    )

    parser.add_argument(
        '--gpu-mem-danger',
        type=int,
        metavar='INT',
        help='GPU memory danger threshold %%'
    )

    parser.add_argument(
        '-v', '--version',
        action='version',
        version='GPU Monitor 1.0'
    )

    parser.add_argument(
        '--ui',
        choices=['v1', 'v2'],
        default='v2',
        help='UI version: v1 (classic) or v2 (progress bars), default: v2'
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()

    # Load configuration
    config = load_config(args.config)

    # Override with command line arguments
    if args.refresh_rate is not None:
        config.refresh_rate = args.refresh_rate

    if args.log_dir is not None:
        config.log_dir = args.log_dir

    if args.log_retention is not None:
        config.log_retention_days = args.log_retention

    if args.no_log:
        config.log_enabled = False

    if args.gpu_util_warning is not None:
        config.alerts.gpu_util_warning = args.gpu_util_warning

    if args.gpu_util_danger is not None:
        config.alerts.gpu_util_danger = args.gpu_util_danger

    if args.gpu_mem_warning is not None:
        config.alerts.gpu_mem_warning = args.gpu_mem_warning

    if args.gpu_mem_danger is not None:
        config.alerts.gpu_mem_danger = args.gpu_mem_danger

    # Run application
    app = GPUMonitorApp(config, ui_version=args.ui)
    sys.exit(app.run())


if __name__ == '__main__':
    main()

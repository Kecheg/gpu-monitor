#!/usr/bin/env python3
"""Analyze GPU monitor logs and create charts."""

import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Settings
LOG_FILE = "/var/log/gpu_monitor/gpu_monitor_20260518.log"
START_HOUR = 19  # 19:00

def parse_log_line(line):
    """Parse a single log line and extract GPU data."""
    # Extract timestamp
    ts_match = re.match(r'(\d{4}-\d{2}-\d{2} (\d{2}:\d{2}:\d{2}))', line)
    if not ts_match:
        return None, None
    timestamp_str = ts_match.group(2)
    timestamp = datetime.strptime(f"1970-01-01 {timestamp_str}", "%Y-%m-%d %H:%M:%S")

    # Extract GPU data
    gpu_pattern = r'GPU(\d+):\s*Mem=([\d/]+MB)\(([\d.]+)%\),\s*Util=(\d+)%,\s*Temp=(\d+)°C,\s*Power=([\d.]+)W,\s*PCIe=([\d.]+)MB/s'
    gpus = {}

    for match in re.finditer(gpu_pattern, line):
        gpu_id = int(match.group(1))
        gpus[gpu_id] = {
            'mem_percent': float(match.group(3)),
            'util': int(match.group(4)),
            'temp': int(match.group(5)),
            'power': float(match.group(6)),
            'pcie': float(match.group(7))
        }

    return timestamp, gpus

def load_logs():
    """Load logs starting from specified hour."""
    data = {
        'timestamps': [],
        'gpus': defaultdict(lambda: defaultdict(list))
    }

    with open(LOG_FILE, 'r') as f:
        for line in f:
            # Check if line is from the target hour
            if f' {START_HOUR:02d}:' not in line:
                continue

            timestamp, gpus = parse_log_line(line)
            if timestamp and gpus:
                data['timestamps'].append(timestamp)
                for gpu_id, metrics in gpus.items():
                    for key, value in metrics.items():
                        data['gpus'][gpu_id][key].append(value)

    return data

def create_charts(data):
    """Create line charts for each metric."""
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'GPU Monitor Analysis - Starting {START_HOUR}:00', fontsize=14)

    metrics = [
        ('util', 'GPU Utilization (%)', axes[0, 0], 0, 100),
        ('temp', 'Temperature (°C)', axes[0, 1], 25, 45),
        ('power', 'Power (W)', axes[1, 0], 0, 200),
        ('pcie', 'PCIe Bandwidth (MB/s)', axes[1, 1], 0, 25000)
    ]

    timestamps = data['timestamps']

    for metric_key, title, ax, ymin, ymax in metrics:
        for gpu_id in sorted(data['gpus'].keys()):
            values = data['gpus'][gpu_id][metric_key]
            if values:
                # Plot line with markers only for first and last points to reduce clutter
                ax.plot(timestamps, values, label=f'GPU{gpu_id}', alpha=0.7, linewidth=1.5)

        ax.set_title(title, fontsize=10)
        ax.set_xlabel('Time')
        ax.set_ylabel(title.split('(')[1].rstrip(')'))
        ax.set_ylim(ymin, ymax)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=7, ncol=2)

        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    return fig

def create_combined_chart(data):
    """Create a combined chart showing all metrics for a specific GPU."""
    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    fig.suptitle(f'GPU3 - All Metrics (Starting {START_HOUR}:00)', fontsize=14)

    gpu_id = 3
    if gpu_id not in data['gpus']:
        print(f"GPU {gpu_id} not found in data")
        return None

    timestamps = data['timestamps']

    # Plot each metric
    configs = [
        ('util', 'Utilization (%)', axes[0], 'green', 0, 100),
        ('temp', 'Temperature (°C)', axes[1], 'red', 25, 45),
        ('power', 'Power (W)', axes[2], 'blue', 0, 200),
        ('pcie', 'PCIe Bandwidth (MB/s)', axes[3], 'purple', 0, 25000)
    ]

    for metric_key, title, ax, color, ymin, ymax in configs:
        values = data['gpus'][gpu_id].get(metric_key, [])
        if values:
            ax.fill_between(timestamps, values, alpha=0.3, color=color)
            ax.plot(timestamps, values, color=color, linewidth=1.5)

        ax.set_ylabel(title)
        ax.set_ylim(ymin, ymax)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel('Time')
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    return fig

def main():
    """Main function."""
    print(f"Loading logs from {LOG_FILE} starting {START_HOUR}:00...")
    data = load_logs()

    print(f"Loaded {len(data['timestamps'])} data points")
    print(f"Found data for GPUs: {sorted(data['gpus'].keys())}")

    # Create individual metric charts
    print("\nCreating metric comparison charts...")
    fig1 = create_charts(data)
    fig1.savefig('/tmp/gpu_metrics_comparison.png', dpi=100, bbox_inches='tight')
    print("Saved: /tmp/gpu_metrics_comparison.png")

    # Create combined chart for GPU3
    print("\nCreating combined chart for GPU3...")
    fig2 = create_combined_chart(data)
    if fig2:
        fig2.savefig('/tmp/gpu3_combined.png', dpi=100, bbox_inches='tight')
        print("Saved: /tmp/gpu3_combined.png")

    print("\nDone! Charts saved to /tmp/")
    print("You can view them with: eog /tmp/gpu_*.png or display /tmp/gpu_*.png")

if __name__ == '__main__':
    main()

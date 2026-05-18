# GPU Monitor

A real-time GPU monitoring tool for NVIDIA GPUs with an interactive terminal UI similar to htop.

## Features

- **Real-time monitoring** of GPU utilization, memory, temperature, power, and clock speeds
- **PCIe bandwidth tracking** with separate TX/RX monitoring
- **Progress bar visualization** (V2 UI) for intuitive metric display
- **Top processes display** showing GPU memory usage per process
- **Color-coded alerts** for warning and danger thresholds
- **Interactive navigation** using keyboard
- **Configurable alerts** via YAML configuration or command line
- **Automatic logging** with daily rotation and compression
- **Two UI modes**: Classic (V1) and Progress Bars (V2, default)

## Requirements

- Python 3.7+
- NVIDIA GPU with proprietary drivers (nvidia-smi required)
- Linux system

## Dependencies

```
psutil>=5.9.0
PyYAML>=6.0
```

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd gpu_monitor

# Install dependencies
pip install -r requirements.txt

# Install with setup.py (recommended)
pip install -e .
```

This will create the `gpu_monitor` command in your path.

## Usage

### Basic Usage

```bash
# Run with default V2 UI (progress bars)
gpu_monitor

# Or use python directly
python gpu_monitor.py
```

### Command Line Options

```bash
gpu_monitor [OPTIONS]

Options:
  -r, --refresh-rate SECONDS    Refresh interval [1-10], default: 2
  -c, --config FILE            Configuration file path
  -l, --log-dir DIR            Log directory
  -d, --log-retention DAYS     Log retention days, default: 7
  --no-log                     Disable logging
  --ui {v1,v2}                 UI version: v1 (classic) or v2 (progress bars), default: v2
  --gpu-util-warning INT       GPU utilization warning threshold %
  --gpu-util-danger INT        GPU utilization danger threshold %
  --gpu-mem-warning INT        GPU memory warning threshold %
  --gpu-mem-danger INT         GPU memory danger threshold %
  -h, --help                   Show help
  -v, --version                Show version
```

### Examples

```bash
# Use V1 classic UI
gpu_monitor --ui v1

# Refresh every 5 seconds
gpu_monitor -r 5

# Custom warning thresholds
gpu_monitor --gpu-util-warning 80 --gpu-mem-warning 90

# Disable logging
gpu_monitor --no-log

# Use custom config file
gpu_monitor -c ~/.config/gpu_monitor/custom_config.yaml
```

## Keyboard Controls

- `q` / `ESC`: Exit
- `←` `→`: Select GPU card
- `r`: Manual refresh
- `+` `-`: Adjust refresh interval (1-10 seconds)

## UI Modes

### V2 (Default) - Progress Bars

Visual display with progress bars showing current values vs limits:

```
GPU0 [RTX 4090]
Mem:       [████████░] 21|24GB (85%)
Util:      [███████░░] 85%|100%
Temp:      [███░░░░░░] 42°C|85°C (49%)
Pwr:       [████░░░░░] 250|350W (71%)
Clk:       [██████░░░] 1800|1900MHz (95%)
PCIe-TX:   [██████░░░] 15.0|32GB/s (47%)
PCIe-RX:   [░░░░░░░░░] 512MB/s|32GB/s (2%)
PCIe-Total:[████░░░░░] 15.5|64GB/s (24%)
```

### V1 - Classic

Compact text-based display:

```
GPU0
RTX 4090
Mem: 21/24GB
Util: 85%
Temp: 42°C
Pwr: 250/350W (71%)
Clk: 1800/1900MHz (95%)
PCIe-TX: 15.0GB/s
PCIe-RX: 512MB/s
PCIe-Total: 15.5GB/s
```

## Configuration

Configuration files are loaded in the following order (later files override earlier ones):

1. Command line arguments (highest priority)
2. `~/.config/gpu_monitor/config.yaml`
3. `/etc/gpu_monitor/config.yaml`
4. Default configuration (lowest priority)

### Example Configuration

```yaml
# config/default_config.yaml

# Monitoring settings
refresh_rate: 2
gpu_count: 8

# Alert thresholds
alerts:
  gpu_util_warning: 90
  gpu_util_danger: 95
  gpu_mem_warning: 95
  gpu_mem_danger: 98
  gpu_temp_warning: 80
  gpu_temp_danger: 85
  cpu_mem_warning: 85
  cpu_mem_danger: 95

# Logging settings
log_enabled: true
log_dir: /var/log/gpu_monitor
log_retention_days: 7

# Display settings
ui_version: v2  # v1 or v2
```

## Alert Colors

- **Green**: Normal status (< 80%)
- **Yellow**: Warning threshold (80-95%)
- **Red**: Danger threshold (≥ 95%)

## Logging

Logs are written daily with automatic rotation and compression:

```
/var/log/gpu_monitor/
├── gpu_monitor_20260518.log
├── gpu_monitor_20260517.log
├── gpu_monitor_20260516.log.gz
└── ...
```

Log format:
```
2026-05-18 19:09:29 | GPU0: Mem=21058/24564MB(85.7%), Util=0%, Temp=30°C, Power=14W, PCIe-TX=11.0MB/s, PCIe-RX=0.0MB/s | ...
```

If `/var/log/gpu_monitor/` is not writable, logs fallback to `~/.local/share/gpu_monitor/`.

## PCIe Bandwidth Limits

Progress bars show PCIe bandwidth relative to Gen4 x16 theoretical maximum:
- **TX/RX**: 32 GB/s per direction
- **Total**: 64 GB/s (combined)

## Project Structure

```
gpu_monitor/
├── gpu_monitor.py              # Main entry point
├── core/
│   ├── __init__.py
│   ├── nvidia_collector.py     # NVIDIA GPU data collection (unified)
│   ├── cpu_monitor.py          # CPU/memory monitoring
│   └── alert_manager.py        # Alert threshold management
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # V1 curses main window
│   ├── gpu_panel.py            # V1 GPU info panel
│   ├── main_window_v2.py       # V2 curses main window (progress bars)
│   └── gpu_panel_v2.py         # V2 GPU info panel (progress bars)
├── utils/
│   ├── __init__.py
│   ├── config.py               # Configuration management
│   └── logger.py               # Logging with rotation
└── config/
    └── default_config.yaml     # Default configuration
```

## Performance

- Refresh interval: 1-10 seconds (default: 2s)
- CPU overhead: < 1%
- Memory usage: < 50MB

## License

MIT License

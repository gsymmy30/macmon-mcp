# MacMon MCP Server

System monitoring for macOS through Claude Desktop. MacMon provides real-time insights into CPU, memory, disk, and network usage directly within your Claude conversations.

## Features

- System resource monitoring (CPU, memory, disk, swap)
- Process tracking with sorting by resource usage
- Network statistics and interface information
- Per-core CPU usage and load averages
- Automatic alerts for high resource consumption

## Requirements

- macOS
- Python 3.8+
- Claude Desktop

## Installation

Clone and set up the environment:

```bash
git clone https://github.com/gsymmy30/macmon-mcp.git
cd macmon-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Configure Claude Desktop by adding to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "macmon": {
      "command": "/absolute/path/to/macmon-mcp/venv/bin/python",
      "args": ["/absolute/path/to/macmon-mcp/server.py"]
    }
  }
}
```

Replace paths with your actual installation directory (use `pwd` to get the full path).

Restart Claude Desktop to load the server.

## Usage

Ask Claude questions like:
- "Check my system status"
- "Show me top processes by memory"
- "What's my network usage?"
- "Check for system alerts"

## Testing

Run the test suite to verify installation:

```bash
python server.py --test
```

## Available Commands

| Command | Description |
|---------|-------------|
| `get_system_status` | System overview with all metrics |
| `get_top_processes` | List processes by CPU or memory usage |
| `get_network_stats` | Network transfer and interface data |
| `get_cpu_details` | Per-core usage and frequencies |
| `check_alerts` | Check for high resource usage |

## Alert Thresholds

- CPU: Warning at 80%, Critical at 90%
- Memory: Warning at 85%, Critical at 95%
- Disk: Warning at 90%, Critical at 95%
- Swap: Warning at 75%

## Troubleshooting

If MacMon isn't appearing in Claude:
1. Verify absolute paths in the config file
2. Ensure Claude Desktop was fully restarted
3. Check the developer console (Cmd+Option+I) for errors
4. Run `python server.py --test` to verify the server works

## License

MIT

## Author

Gursimran Singh ([@gsymmy30](https://github.com/gsymmy30))
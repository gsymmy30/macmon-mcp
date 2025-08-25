#!/usr/bin/env python3
"""
MacMon MCP Server - macOS System Monitoring for Claude
"""

import asyncio
import psutil
import sys
import json
from datetime import datetime
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Initialize MacMon server
server = Server("macmon")

def format_bytes(bytes):
    """Convert bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.1f}{unit}"
        bytes /= 1024.0
    return f"{bytes:.1f}PB"

def format_uptime(boot_time):
    """Format uptime in a readable way."""
    uptime_seconds = (datetime.now() - datetime.fromtimestamp(boot_time)).total_seconds()
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def check_system_alerts():
    """Check system metrics and return alerts if thresholds are exceeded."""
    alerts = []
    
    # Check CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent > 80:
        alerts.append({
            'level': 'high' if cpu_percent > 90 else 'medium',
            'type': 'CPU',
            'message': f'CPU usage is {cpu_percent}%',
            'value': cpu_percent
        })
    
    # Check Memory
    memory = psutil.virtual_memory()
    if memory.percent > 85:
        alerts.append({
            'level': 'high' if memory.percent > 95 else 'medium',
            'type': 'Memory',
            'message': f'Memory usage is {memory.percent}%',
            'value': memory.percent
        })
    
    # Check Disk
    disk = psutil.disk_usage('/')
    if disk.percent > 90:
        alerts.append({
            'level': 'high' if disk.percent > 95 else 'medium',
            'type': 'Disk',
            'message': f'Disk usage is {disk.percent}%',
            'value': disk.percent
        })
    
    # Check Swap (if it's being used heavily)
    swap = psutil.swap_memory()
    if swap.percent > 75:
        alerts.append({
            'level': 'medium',
            'type': 'Swap',
            'message': f'Swap usage is {swap.percent}%',
            'value': swap.percent
        })
    
    return alerts

def get_system_status():
    """Get system status."""
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    disk = psutil.disk_usage('/')
    
    boot_time = psutil.boot_time()
    uptime = format_uptime(boot_time)
    
    status = f"""🖥️ **MacMon System Status**

**CPU**
- Usage: {cpu_percent}% ({cpu_count} cores)
- Load Average: {', '.join(map(str, psutil.getloadavg()))}

**Memory**
- RAM: {memory.percent}% used ({format_bytes(memory.used)} / {format_bytes(memory.total)})
- Swap: {swap.percent}% used ({format_bytes(swap.used)} / {format_bytes(swap.total)})
- Available: {format_bytes(memory.available)}

**Storage**
- Disk Usage: {disk.percent}% used
- Used: {format_bytes(disk.used)} / {format_bytes(disk.total)}
- Free: {format_bytes(disk.free)}

**System**
- Uptime: {uptime}
- Boot Time: {datetime.fromtimestamp(boot_time).strftime('%Y-%m-%d %H:%M:%S')}"""
    
    return status

def get_top_processes(limit=10, sort_by='cpu'):
    """Get top processes by CPU or memory usage."""
    processes = []
    
    # First, trigger CPU percent calculation
    for proc in psutil.process_iter(['cpu_percent']):
        pass
    
    # Small delay to get accurate CPU readings
    import time
    time.sleep(0.1)
    
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
        try:
            pinfo = proc.info
            
            # Get values with defaults for None
            pid = pinfo.get('pid', 0)
            name = pinfo.get('name', 'Unknown')
            cpu_percent = pinfo.get('cpu_percent') or 0.0
            memory_percent = pinfo.get('memory_percent') or 0.0
            
            # Get memory in MB
            memory_mb = 0
            if pinfo.get('memory_info') and hasattr(pinfo['memory_info'], 'rss'):
                memory_mb = pinfo['memory_info'].rss / 1024 / 1024
            
            processes.append({
                'pid': pid,
                'name': name,
                'cpu_percent': float(cpu_percent),
                'memory_percent': float(memory_percent),
                'memory_mb': memory_mb
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as e:
            continue
    
    # Sort by the specified metric
    if sort_by == 'memory':
        processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
    else:
        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
    
    # Format the output
    result = f"🔝 **Top {limit} Processes by {sort_by.upper()}**\n\n"
    for i, proc in enumerate(processes[:limit], 1):
        result += f"{i}. **{proc['name']}** (PID: {proc['pid']})\n"
        result += f"   • CPU: {proc['cpu_percent']:.1f}%\n"
        result += f"   • Memory: {proc['memory_percent']:.1f}% ({proc['memory_mb']:.1f} MB)\n\n"
    
    return result

def get_network_stats():
    """Get network statistics."""
    stats = psutil.net_io_counters()
    
    result = f"""🌐 **Network Statistics**

**Data Transfer**
- Sent: {format_bytes(stats.bytes_sent)}
- Received: {format_bytes(stats.bytes_recv)}

**Packets**
- Sent: {stats.packets_sent:,}
- Received: {stats.packets_recv:,}
- Errors: {stats.errin + stats.errout:,}
- Dropped: {stats.dropin + stats.dropout:,}"""
    
    # Add network interfaces
    addrs = psutil.net_if_addrs()
    active_interfaces = []
    for interface, addr_list in addrs.items():
        for addr in addr_list:
            if addr.family == 2:  # IPv4
                active_interfaces.append(f"• {interface}: {addr.address}")
    
    if active_interfaces:
        result += "\n\n**Active Interfaces**\n" + "\n".join(active_interfaces)
    
    return result

def get_cpu_details():
    """Get detailed CPU information."""
    cpu_percent_per_core = psutil.cpu_percent(interval=1, percpu=True)
    
    result = f"""🔧 **Detailed CPU Information**

**Overall**
- Physical Cores: {psutil.cpu_count(logical=False)}
- Logical Cores: {psutil.cpu_count(logical=True)}
"""
    
    # CPU frequency might not be available on all systems
    try:
        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            result += f"• Current Frequency: {cpu_freq.current:.2f} MHz\n"
            if cpu_freq.max > 0:
                result += f"• Max Frequency: {cpu_freq.max:.2f} MHz\n"
    except:
        pass
    
    result += "\n**Per-Core Usage**\n"
    for i, percent in enumerate(cpu_percent_per_core):
        result += f"• Core {i}: {percent}%\n"
    
    result += f"\n**Load Average**\n"
    load1, load5, load15 = psutil.getloadavg()
    result += f"• 1 min: {load1:.2f}\n"
    result += f"• 5 min: {load5:.2f}\n"
    result += f"• 15 min: {load15:.2f}"
    
    return result

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available MacMon tools."""
    return [
        types.Tool(
            name="get_system_status",
            description="Get current macOS system status including CPU, memory, and disk usage",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="get_top_processes",
            description="Get the top processes by CPU or memory usage",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of processes to show (default: 10)",
                        "default": 10
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sort by 'cpu' or 'memory' (default: 'cpu')",
                        "enum": ["cpu", "memory"],
                        "default": "cpu"
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_network_stats",
            description="Get network statistics including data transfer and active interfaces",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="get_cpu_details",
            description="Get detailed CPU information including per-core usage and frequency",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="check_alerts",
            description="Check system metrics and report any alerts for high resource usage",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """Execute MacMon tools."""
    
    if name == "get_system_status":
        status = get_system_status()
        return [types.TextContent(type="text", text=status)]
    
    elif name == "get_top_processes":
        limit = arguments.get("limit", 10) if arguments else 10
        sort_by = arguments.get("sort_by", "cpu") if arguments else "cpu"
        result = get_top_processes(limit, sort_by)
        return [types.TextContent(type="text", text=result)]
    
    elif name == "get_network_stats":
        result = get_network_stats()
        return [types.TextContent(type="text", text=result)]
    
    elif name == "get_cpu_details":
        result = get_cpu_details()
        return [types.TextContent(type="text", text=result)]
    
    elif name == "check_alerts":
        alerts = check_system_alerts()
        
        if not alerts:
            return [types.TextContent(type="text", text="✅ All systems normal - no alerts")]
        
        # Format alert response
        response = "⚠️ **System Alerts**\n\n"
        for alert in alerts:
            emoji = "🔴" if alert['level'] == 'high' else "🟡"
            response += f"{emoji} **{alert['type']}**: {alert['message']}\n"
        
        return [types.TextContent(type="text", text=response)]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Run the MacMon MCP server."""
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("🧪 MacMon Test Mode\n")
        print("1. System Status:")
        print(get_system_status())
        print("\n2. Top 5 Processes:")
        try:
            print(get_top_processes(5))
        except Exception as e:
            print(f"Error getting processes: {e}")
        print("\n3. Network Stats:")
        try:
            print(get_network_stats())
        except Exception as e:
            print(f"Error getting network stats: {e}")
        print("\n4. CPU Details:")
        try:
            print(get_cpu_details())
        except Exception as e:
            print(f"Error getting CPU details: {e}")
        print("\n5. Checking Alerts:")
        alerts = check_system_alerts()
        if alerts:
            for alert in alerts:
                print(f"- {alert['type']}: {alert['message']}")
        else:
            print("No alerts")
        print("\n✅ MacMon testing complete!")
        return
    
    # Normal MCP server mode
    print("Starting MacMon MCP Server v0.2.3...", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="macmon",
                server_version="0.2.3",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMacMon server stopped.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
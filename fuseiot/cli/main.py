import asyncio
import sys
import json
import click
from typing import Optional

from fuseiot import Hub, HTTP, Switchable, Sensor, auto_config, configure_logging, get_logger
from fuseiot.discovery.mdns import MDNSDiscovery

logger = get_logger("cli")


@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, config, verbose):
    """FuseIoT - Deterministic device control CLI."""
    ctx.ensure_object(dict)
    
    # Load configuration
    cfg = auto_config(config)
    configure_logging(
        level="DEBUG" if verbose else cfg.log_level,
        json_format=False
    )
    
    ctx.obj['config'] = cfg
    ctx.obj['hub'] = Hub(cfg)


@cli.command()
@click.pass_context
def discover(ctx):
    """Discover devices on network."""
    click.echo("Scanning for devices...")
    
    discovery = MDNSDiscovery()
    devices = discovery.scan(timeout=5)
    
    if not devices:
        click.echo("No devices found.")
        return
    
    click.echo(f"\nFound {len(devices)} devices:")
    for device in devices:
        click.echo(f"  {device.name} @ {device.address}:{device.port}")
        click.echo(f"    Type: {device.device_type}")
        click.echo(f"    Protocol: {device.protocol}")


@cli.command()
@click.argument('device_id')
@click.pass_context
def status(ctx, device_id):
    """Get device status."""
    hub = ctx.obj['hub']
    
    try:
        device = hub[device_id]
        state = device.read_state()
        
        click.echo(f"Device: {device_id}")
        click.echo(f"Category: {device.category}")
        click.echo(f"Protocol: {device.protocol.name}")
        click.echo(f"State: {json.dumps(state, indent=2)}")
        
    except KeyError:
        click.echo(f"Device not found: {device_id}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('device_id')
@click.option('--confirm/--no-confirm', default=True, help='Wait for confirmation')
@click.option('--timeout', '-t', default=5.0, help='Timeout in seconds')
@click.pass_context
def on(ctx, device_id, confirm, timeout):
    """Turn device on."""
    hub = ctx.obj['hub']
    
    try:
        device = hub[device_id]
        result = device.on(confirm=confirm, timeout=timeout)
        
        if result.success:
            symbol = "✓" if result.confirmed else "~"
            click.echo(f"{symbol} {device_id} turned on ({result.latency_ms:.0f}ms)")
        else:
            click.echo(f"✗ Failed: {result.error}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('device_id')
@click.option('--confirm/--no-confirm', default=True)
@click.option('--timeout', '-t', default=5.0)
@click.pass_context
def off(ctx, device_id, confirm, timeout):
    """Turn device off."""
    hub = ctx.obj['hub']
    
    try:
        device = hub[device_id]
        result = device.off(confirm=confirm, timeout=timeout)
        
        if result.success:
            symbol = "✓" if result.confirmed else "~"
            click.echo(f"{symbol} {device_id} turned off ({result.latency_ms:.0f}ms)")
        else:
            click.echo(f"✗ Failed: {result.error}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def list_devices(ctx):
    """List all registered devices."""
    hub = ctx.obj['hub']
    
    devices = hub.list_devices(as_dict=True)
    
    if not devices:
        click.echo("No devices registered.")
        return
    
    click.echo(f"{'Device ID':<30} {'Category':<15} {'Status'}")
    click.echo("-" * 60)
    
    for device_id, category in devices.items():
        try:
            device = hub[device_id]
            connected = "●" if device.protocol.is_connected else "○"
            click.echo(f"{device_id:<30} {category:<15} {connected}")
        except:
            click.echo(f"{device_id:<30} {category:<15} ?")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show hub statistics."""
    hub = ctx.obj['hub']
    stats = hub.stats()
    
    click.echo(json.dumps(stats, indent=2, default=str))


def main():
    """Entry point."""
    cli()


if __name__ == '__main__':
    main()
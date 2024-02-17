import argparse

from rx.client import grpc_helper
from rx.client.commands import command
from rx.client.commands import daemon
from rx.daemon import client
from rx.daemon import pidfile

class Command(daemon.DaemonCommand):
  """Parent class that handles connecting to the daemon RPC server."""

  def __init__(self, cmdline: command.CommandLine) -> None:
    super().__init__(cmdline)
    self._pidfile = pidfile.PidFile(self.local_config.cwd)

  def _run(self) -> int:
    if not self._pidfile.is_running():
      # Daemon isn't running, attempt to start.
      # This hangs if we open a GRPC channel before forking, so only check the
      # pid file before the get_channel below.
      if not daemon.start_daemon(self.local_config):
        # Unable to start the daemon.
        return -1

    # Now that we (maybe) forked, create GRPC connection.
    daemon_addr = f'localhost:{self.local_config.daemon_port}'
    with grpc_helper.get_channel(daemon_addr) as ch:
      cli = client.Client(ch, self.local_config)
      try:
        return self._call_daemon(cli)
      except client.DaemonUnavailable as e:
        print(f'Could not connect to daemon: {e}')
        return -1

  def _call_daemon(self, daemon_cli: client.Client) -> int:
    del daemon_cli
    raise NotImplementedError()


class OpenPortCommand(Command):
  """Sets up port forwarding for a port."""

  def _call_daemon(self, daemon_cli: client.Client) -> int:
    if not self._cmdline.remainder:
      raise argparse.ArgumentError(None, 'Port must be specified')
    port = int(self._cmdline.remainder[0])
    if not port:
      raise argparse.ArgumentError(
        None, f'Invalid port number: {self._cmdline.remainder[0]}')
    local_port = self._cmdline.ns.local_port
    daemon_cli.open_port(port=port, local_port=local_port)
    local_mapping = ''
    if local_port:
      local_mapping = f' to localhost:{local_port}'
    print(f'Forwarded port {port}{local_mapping}')
    return 0


class ClosePortCommand(Command):
  """Tears down port forwarding for a port."""

  def _call_daemon(self, daemon_cli: client.Client) -> int:
    if not self._cmdline.remainder:
      raise argparse.ArgumentError(None, 'Port must be specified')
    port = int(self._cmdline.remainder[0])
    if not port:
      raise argparse.ArgumentError(
        None, f'Invalid port number: {self._cmdline.remainder[0]}')
    daemon_cli.close_port(port)
    print(f'Closed port {port}')
    return 0


class PortInfoCommand(Command):
  """Shows info about port forwarding for this workspace."""

  def _call_daemon(self, daemon_cli: client.Client) -> int:
    info = daemon_cli.info()
    print(daemon.format_info(info))
    return 0


def add_parser(subparsers: argparse._SubParsersAction):
  open_port_cmd = subparsers.add_parser(
    'open-port', help='Forwards a port on the workspace to this machine')
  open_port_cmd.add_argument(
    '--local-port', dest='local_port', type=int, default=0,
    help='Port to forward to listen on locally')
  open_port_cmd.set_defaults(cmd=OpenPortCommand)

  close_port_cmd = subparsers.add_parser(
    'close-port', help='Stop forwarding to a port')
  close_port_cmd.set_defaults(cmd=ClosePortCommand)

  port_info_cmd = subparsers.add_parser(
    'ports', help='Show ports being forwarded')
  port_info_cmd.set_defaults(cmd=PortInfoCommand)

import contextlib
import subprocess
import sys
import tempfile
import time
from typing import Generator, cast

import grpc
from google.protobuf import empty_pb2

from rx.client import grpc_helper
from rx.client.configuration import config_base
from rx.client.configuration import local
from rx.daemon import client
from rx.daemon import pidfile
from rx.proto import daemon_pb2_grpc


class DaemonManager:
  def __init__(self, local_cfg: local.LocalConfig) -> None:
    self._local_cfg = local_cfg
    self._pidfile = pidfile.PidFile(self._local_cfg.cwd)
    self._daemon_addr = f'localhost:{self._local_cfg.daemon_port}'

  @property
  def daemon_addr(self) -> str:
    return self._daemon_addr

  @contextlib.contextmanager
  def get_daemon_client(self) -> Generator[client.Client, None, None]:
    daemon_addr = f'localhost:{self._local_cfg.daemon_port}'
    ch = grpc_helper.get_channel(daemon_addr)
    cli = client.Client(ch, self._local_cfg)
    try:
        yield cli
    finally:
        ch.close()

  def maybe_start_daemon(self) -> bool:
    """Returns if the daemon is running when this returns."""
    if self._pidfile.is_running():
      return True

    pretty_file = self._pidfile.filename.relative_to(self._local_cfg.cwd)
    print(f'Daemon specified in {pretty_file} isn\'t running.')

    # Daemon isn't running, attempt to start.
    # This hangs if we open a GRPC channel before forking, so only check the
    # pid file before the get_channel below.
    try:
      if self.start_daemon():
        return True

      # Unable to start the daemon. Now we're in the chute to return False
      # regardless, but attempt to kill the unwanted daemon on the way. Maybe it
      # is already listening on the port we want. Try to connect and kill it.
      self.connect_and_kill()
    except client.RetryError:
      print(
        'Killed the existing daemon, please re-run your command to start a new '
        'one.')
    return False

  def start_daemon(self) -> bool:
    """Starts the daemon. Returns if successful."""
    port = self._local_cfg.daemon_port
    trex_addr = config_base.TREX_HOST.value
    # This is a vanilla Popen: the daemon is its grandchild!
    subprocess.Popen([
      'rx-daemon',
      f'--port={port}',
      f'--trex-host={trex_addr}',
      f'--rxroot={self._local_cfg.cwd}',
    ])
    print(f'Daemon started at localhost:{port}')

    # Now (try to) connect to it to make sure it's running.
    sys.stdout.write('Checking daemon is running...')
    sys.stdout.flush()
    tries = 5
    with grpc_helper.get_channel(self._daemon_addr) as ch:
      for _ in range(tries):
        time.sleep(1)
        try:
          cli = client.Client(ch, self._local_cfg)
          if cli.is_running():
            sys.stdout.write(' Connected!\n')
            return True
        except pidfile.NotFoundError:
          # The daemon might not have created the pid file yet.
          pass
        sys.stdout.write('.')
        sys.stdout.flush()

    logfile = f'{tempfile.gettempdir()}/rx-daemon.INFO'
    print(f'Unable to connect to daemon, check {logfile} for details')
    return False

  def connect_and_kill(self) -> bool:
    """Returns if the daemon is no longer running."""
    try:
      # This connection is made manually, as Client attempts to look up the pid
      # which we don't have.
      with grpc_helper.get_channel(self._daemon_addr) as ch:
        stub = daemon_pb2_grpc.PortForwardingServiceStub(ch)
        stub.GetPorts(
          empty_pb2.Empty(),
          # We don't have a pid to send.
          metadata=(('cv', local.VERSION), ('pid', 'unknown')))
        assert False, (
          'If the daemon was running at the right version/pid, killing by pid '
          'should have worked')
    except grpc.RpcError as e:
      e = cast(grpc.Call, e)
      try:
        client.handle_rpc_error(e)
      except client.DaemonUnavailable as e2:
        # We could not connect to the daemon.
        print(f'Could not send request to connect and kill: {e2}')
        return True
      print(f'Request failed: {e.details()}')
      return False

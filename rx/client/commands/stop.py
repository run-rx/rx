import pathlib
import sys

from rx.client import grpc_helper
from rx.client import trex_client
from rx.client.commands import command
from rx.client.configuration import config_base
from rx.client.configuration import local


class StopCommand(command.Command):
  """Initialize (or reinitialize) the remote."""

  def run(self) -> int:
    if not self._rxroot:
      sys.stderr.write(f'Could not find rx root in {pathlib.Path.cwd()}\n')
      sys.stderr.flush()
      return -1

    try:
      config = local.create_local_config(self._rxroot)
      with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
        client = trex_client.create_authed_client(ch, config)
        client.stop()
    except trex_client.TrexError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return e.code

    return 0


if __name__ == '__main__':
  print('Call exec.')

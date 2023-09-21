import sys

from absl import flags

from rx.client import grpc_helper
from rx.client import trex_client
from rx.client.commands import command
from rx.client.configuration import config_base

_UNSUBSCRIBE = flags.DEFINE_bool(
  'unsubscribe', False, 'Stop all machines and halt rx subscription.')


class StopCommand(command.Command):
  """Initialize (or reinitialize) the remote."""

  def run(self) -> int:
    try:
      with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
        client = trex_client.create_authed_client(ch, self.local_config)
        client.stop(
          self.remote_config.workspace_id, unsubscribe=_UNSUBSCRIBE.value)
    except config_base.ConfigNotFoundError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return -1
    except trex_client.TrexError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return e.code
    return 0


if __name__ == '__main__':
  print('Call exec.')

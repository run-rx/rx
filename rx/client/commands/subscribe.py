import sys

from rx.client import grpc_helper
from rx.client import trex_client
from rx.client.commands import command
from rx.client.configuration import config_base


class SubscribeCommand(command.Command):
  """Create a subscription."""

  def run(self) -> int:
    try:
      with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
        client = trex_client.create_authed_client(ch, self.local_config)
        client.subscribe()
    except trex_client.TrexError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return e.code
    return 0


class UnsubscribeCommand(command.Command):
  """Cancel a subscription."""

  def run(self) -> int:
    try:
      with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
        client = trex_client.create_authed_client(ch, self.local_config)
        client.unsubscribe()
    except trex_client.TrexError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return e.code
    return 0


if __name__ == '__main__':
  print('Call exec.')

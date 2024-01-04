import argparse
import sys
from typing import List

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
    except config_base.ConfigNotFoundError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return -1
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
    except config_base.ConfigNotFoundError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return -1
    except trex_client.TrexError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return e.code

    print("""
Your subscription has been canceled.

Please contact us at hello@run-rx.com if you have any feedback.""")
    return 0


def _sub(args: List[str]) -> int:
  del args
  s = SubscribeCommand()
  return s.run()


def _unsub(args: List[str]) -> int:
  del args
  s = UnsubscribeCommand()
  return s.run()


def add_parsers(subparsers: argparse._SubParsersAction):
  (
    subparsers
    .add_parser(
      'subscribe', help='Creates up a new subscription to access rx resources')
    .set_defaults(func=_sub)
  )
  (
    subparsers
    .add_parser('unsubscribe', help='Cancels an existing subscription')
    .set_defaults(func=_unsub)
  )



if __name__ == '__main__':
  print('Call exec.')

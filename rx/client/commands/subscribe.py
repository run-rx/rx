import argparse
import sys
from typing import List

from rx.client import grpc_helper
from rx.client import trex_client
from rx.client.commands import command
from rx.client.configuration import config_base


class SubscribeCommand(command.TrexCommand):
  """Create a subscription."""

  def _run(self) -> int:
    with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
      client = trex_client.create_authed_client(ch, self.local_config)
      client.subscribe()
    return 0


class UnsubscribeCommand(command.TrexCommand):
  """Cancel a subscription."""

  def _run(self) -> int:
    with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
      client = trex_client.create_authed_client(ch, self.local_config)
      client.unsubscribe()

    print("""
Your subscription has been canceled.

Please contact us at hello@run-rx.com if you have any feedback.""")
    return 0


def add_parsers(subparsers: argparse._SubParsersAction):
  (
    subparsers
    .add_parser(
      'subscribe', help='Creates up a new subscription to access rx resources')
    .set_defaults(cmd=SubscribeCommand)
  )
  (
    subparsers
    .add_parser('unsubscribe', help='Cancels an existing subscription')
    .set_defaults(cmd=UnsubscribeCommand)
  )


if __name__ == '__main__':
  print('Call exec.')

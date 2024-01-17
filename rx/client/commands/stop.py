import argparse
import sys
from typing import List

import yaml

from rx.client import grpc_helper
from rx.client import trex_client
from rx.client.commands import command
from rx.client.configuration import config_base

class StopCommand(command.TrexCommand):
  """Initialize (or reinitialize) the remote."""

  def _run(self) -> int:
    with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
      sys.stdout.write('Stopping your workspace...\n')
      client = trex_client.create_authed_client(ch, self.local_config)
      image = client.stop(self.remote_config.workspace_id)
    sys.stdout.write('Your remote machine has been shut down.\n')
    if image:
      print(
        '\nIf you\'d like to initialize a new workspace with this state, '
        f'use the following lines in your config:\n\n{yaml.safe_dump(image)}')
    return 0


def add_parser(subparsers: argparse._SubParsersAction):
  (
    subparsers
    .add_parser('stop', help='Stops the current instance')
    .set_defaults(cmd=StopCommand)
  )


if __name__ == '__main__':
  print('Call exec.')

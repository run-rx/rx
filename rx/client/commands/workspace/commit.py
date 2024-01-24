import argparse
import sys

import yaml

from rx.client import grpc_helper
from rx.client import trex_client
from rx.client.commands import command
from rx.client.configuration import config_base

class CommitCommand(command.TrexCommand):
  """Save the current state on the remote."""

  def _run(self) -> int:
    with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
      sys.stdout.write('Storing your workspace...\n')
      client = trex_client.create_authed_client(ch, self.local_config)
      image = client.commit(
        self.remote_config.workspace_id,
        name=self._cmdline.ns.name,
        organization=self._cmdline.ns.organization)
    sys.stdout.write('Your remote machine\'s state has been saved.\n')
    if image:
      print(
        '\nIf you\'d like to initialize a new workspace with this state, '
        f'use the following lines in your config:\n\n{yaml.safe_dump(image)}')
    return 0


def add_parser(subparsers: argparse._SubParsersAction):
  commit_cmd = subparsers.add_parser(
    'commit', help='Stores the current workspace')
  commit_cmd.add_argument(
    '--organization',
    help='The organization to save this workspace on behalf of.')
  commit_cmd.add_argument(
    '--name', help='The name to use for this workspace.')
  commit_cmd.set_defaults(cmd=CommitCommand)

import sys

import yaml

from rx.client import grpc_helper
from rx.client import trex_client
from rx.client.commands import command
from rx.client.configuration import config_base

class CommitCommand(command.TrexCommand):
  """Save the current state on the remote."""

  def run(self) -> int:
    with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
      sys.stdout.write('Storing your workspace...\n')
      client = trex_client.create_authed_client(ch, self.local_config)
      image = client.stop(self.remote_config.workspace_id, save=True)
    sys.stdout.write('Your remote machine\'s state has been saved.\n')
    if image:
      print(
        '\nIf you\'d like to initialize a new workspace with this state, '
        f'use the following lines in your config:\n\n{yaml.safe_dump(image)}')
    return 0

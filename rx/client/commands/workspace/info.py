import datetime

from google.protobuf import json_format
import yaml

from rx.client import grpc_helper
from rx.client import trex_client
from rx.client.commands import command
from rx.client.configuration import config_base


class InfoCommand(command.TrexCommand):
  """Get info about the current workspace."""

  def _run(self) -> int:
    with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
      client = trex_client.create_authed_client(ch, self.local_config)
      info = client.get_info(self.remote_config.workspace_id)

    target_env = json_format.MessageToDict(info.environment)

    # TODO: check if info matches the remote config.
    print(f"""Workspace info for {self.local_config.cwd}

Remote config YAML file:\n\n{yaml.safe_dump(target_env)}""")
    if info.history:
      print('Commands run this month:')
      for cmd in info.history:
        start = datetime.datetime.fromtimestamp(cmd.start_ts)
        print(f'  {start}\t{cmd.cmd}')
    return 0

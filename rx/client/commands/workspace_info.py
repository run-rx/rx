import argparse
import datetime
import sys
from typing import List

from google.protobuf import json_format
import yaml

from rx.client import grpc_helper
from rx.client import trex_client
from rx.client.commands import command
from rx.client.configuration import config_base
from rx.proto import rx_pb2


class WorkspaceInfoCommand(command.Command):
  """Get info about the current workspace."""

  def run(self) -> int:
    try:
      with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
        client = trex_client.create_authed_client(ch, self.local_config)
        info = client.get_info(self.remote_config.workspace_id)
    except config_base.ConfigNotFoundError as e:
      print('No workspace found.')
      return -1
    except trex_client.TrexError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return e.code

    target_env = json_format.MessageToDict(info.environment)

    # TODO: check if info matches the remote config.
    print(f"""Workspace info for {self.local_config.cwd}

Remote config:\n\n{yaml.safe_dump(target_env)}
Commands run this month:
""")
    for cmd in info.history:
      start = datetime.datetime.fromtimestamp(cmd.start_ts)
      print(f'  {start}\t{cmd.cmd}')
    return 0


def _run_cmd(args: List[str]) -> int:
  del args
  cmd = WorkspaceInfoCommand()
  return cmd.run()


def add_parser(subparsers: argparse._SubParsersAction):
  (
    subparsers
    .add_parser('workspace-info', help='Gets info about the current workspace')
    .set_defaults(func=_run_cmd)
  )


if __name__ == '__main__':
  print('Call exec.')

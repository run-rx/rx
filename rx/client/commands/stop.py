import argparse
import sys
from typing import Optional, Sequence

from rx.client import grpc_helper
from rx.client import trex_client
from rx.client.commands import command
from rx.client.configuration import config_base

class StopCommand(command.Command):
  """Initialize (or reinitialize) the remote."""

  def run(self) -> int:
    try:
      with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
        client = trex_client.create_authed_client(ch, self.local_config)
        client.stop(self.remote_config.workspace_id)
    except config_base.ConfigNotFoundError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return -1
    except trex_client.TrexError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return e.code
    return 0


def _run_cmd(args: Optional[Sequence[str]]) -> int:
  del args
  cmd = StopCommand()
  return cmd.run()


def add_parser(subparsers: argparse._SubParsersAction):
  (
    subparsers
    .add_parser('stop', help='Stops the current instance')
    .set_defaults(func=_run_cmd)
  )


if __name__ == '__main__':
  print('Call exec.')

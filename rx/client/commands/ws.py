import argparse

from rx.client.commands.workspace import commit
from rx.client.commands.workspace import info
from rx.client.commands.workspace import set_acls


def add_parser(subparsers: argparse._SubParsersAction):
  ws_cmd = subparsers.add_parser(
    'ws', help='Workspace handling commands')
  subparsers = ws_cmd.add_subparsers(required=True)

  commit.add_parser(subparsers)

  info_cmd = subparsers.add_parser(
    'info', help='Gets info about the current workspace')
  info_cmd.set_defaults(cmd=info.InfoCommand)

  set_acls.add_parser(subparsers)


if __name__ == '__main__':
  print('Call exec.')

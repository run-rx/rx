import argparse

from rx.client.commands.workspace import commit
from rx.client.commands.workspace import info
from rx.client.commands.workspace import set_acls


def add_parser(subparsers: argparse._SubParsersAction):
  (
    subparsers
    .add_parser('workspace-info', help='Workspace handling commands')
    .set_defaults(cmd=info.InfoCommand)
  )

  ws_cmd = subparsers.add_parser(
    'ws', help='Workspace handling commands')
  subparsers = ws_cmd.add_subparsers(required=True)

  commit_cmd = subparsers.add_parser(
    'commit', help='Stores the current workspace')
  commit_cmd.set_defaults(cmd=commit.CommitCommand)

  info_cmd = subparsers.add_parser(
    'info', help='Gets info about the current workspace')
  info_cmd.set_defaults(cmd=info.InfoCommand)

  acl_cmd = subparsers.add_parser(
    'set-acls', help='Stores the current workspace')
  acl_cmd.set_defaults(cmd=set_acls.AclsCommand)


if __name__ == '__main__':
  print('Call exec.')

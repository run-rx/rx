import argparse
import sys

from rx.client import grpc_helper
from rx.client import trex_client
from rx.client.commands import command
from rx.client.configuration import config_base
from rx.proto import rx_pb2

_PUBLIC = 'public'
_PRIVATE = 'private'

_VISIBILITY = (_PUBLIC, _PRIVATE)


class AclsCommand(command.TrexCommand):
  """Sets the ACLs for this workspace.

  TODO: support remove.
  """

  def _run(self) -> int:
    req = rx_pb2.SetAclsRequest(workspace_id=self.remote_config.workspace_id)
    if self._cmdline.ns.visibility:
      req.visibility = self._cmdline.ns.visibility
    elif self._cmdline.ns.add_reader:
      new_reader = self._cmdline.ns.add_reader
      req.add_reader = new_reader
    else:
      print(
        'One of --visibility or --add-reader must be specified',
        file=sys.stderr)
      return -1

    with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
      client = trex_client.create_authed_client(ch, self.local_config)
      response = client.set_acls(req)
    print(
      'Current ACLs\n============\n\n'
      f'Default visibility: {response.visibility}')
    if response.readers:
      print('Readers:')
      for r in response.readers:
        print(f'  * {r}')
    return 0


def add_parser(subparsers: argparse._SubParsersAction):
  acl_cmd = subparsers.add_parser(
    'set-acls', help='Stores the current workspace')
  # We could technically allow both, but the logic gets more complicated around
  # what's allowed so just make people run a few commands for now.
  group = acl_cmd.add_mutually_exclusive_group()
  group.add_argument(
    '--visibility', choices=_VISIBILITY,
    help='Set overall visibility for this workspace\'s container. Changing the '
    'visibility will not clear individual ACLs that have been granted. For '
    'example, if the workspace\'s visibility is set to "public" and user alice '
    'adds bob as a reader then sets the visibilty to "private", bob will still '
    'have read permissions.')
  group.add_argument(
    '--add-reader', dest='add_reader',
    help='The username or organization ID to share this workspace with')
  acl_cmd.set_defaults(cmd=AclsCommand)


class InvalidAcl(RuntimeError):
  """An invalid permissions scheme was specified."""

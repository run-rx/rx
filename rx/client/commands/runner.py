import argparse
from typing import List

from rx.client import worker_client
from rx.client import grpc_helper
from rx.client.commands import command
from rx.client.configuration import config_base


class RunCommand(command.Command):

  def __init__(self, argv: List[str]):
    super().__init__()
    self._argv = argv

  def run(self) -> int:
    try:
      with grpc_helper.get_channel(self.remote_config.worker_addr) as ch:
        client = worker_client.create_authed_client(ch, self.local_config)
        return self._try_exec(client)
    except config_base.ConfigNotFoundError as e:
      print(e)
      return -1

  def _try_exec(self, client: worker_client.Client) -> int:
    """Sends the command to the server."""
    if len(self._argv) < 1:
      print('No command given.')
      return 1

    if len(self._argv) == 1:
      # If this is a quoted arg, break it into pieces. E.g., to pass "ls -l" it
      # must be quoted so that absl doesn't try to capture the -l.
      # TODO: is there a better way to handle this with absl flags?
      self._argv = self._argv[0].split(' ')
    try:
      return client.exec(list(self._argv))
    except KeyboardInterrupt:
      client.maybe_kill()
      return worker_client.SIGINT_CODE
    except worker_client.UnreachableError as e:
      print('Worker was unrechable, run `rx init` to get a new instance.')
      return e.code
    except worker_client.WorkerError as e:
      print(e)
      return e.code
    except grpc_helper.RetryError:
      print('Retrying command...')
      return self._try_exec(client)


def _run_cmd(args: List[str]) -> int:
  cmd = RunCommand(args)
  return cmd.run()


def add_parser(subparsers: argparse._SubParsersAction):
  (
    subparsers
    .add_parser('run', help='Runs a command')
    .set_defaults(func=_run_cmd)
  )

"""rx usage

To set up this directory on a remote host:

    rx init

You only have to run this once per directory, similar to `git init`.

To run a command on the remote host:

    rx CMD

Run 'rx --help' for more options or visit https://docs.run-rx.com.
"""
import argparse
import tempfile
from typing import List, Optional, Sequence

from absl import app
from absl import logging
from absl.flags import argparse_flags

from rx.client import worker_client
from rx.client import grpc_helper
from rx.client.commands import command
from rx.client.commands import init
from rx.client.commands import stop
from rx.client.commands import subscribe
from rx.client.commands import workspace_info
from rx.client.configuration import config_base
from rx.client.configuration import local


class ExecCommand(command.Command):

  def __init__(self, argv: Sequence[str]):
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


def _get_version(args: Optional[Sequence[str]]) -> int:
  del args
  print(local.VERSION)
  return 0


def _run_cmd(args: Optional[Sequence[str]]) -> int:
  assert args
  cmd = ExecCommand(args)
  return cmd.run()


def get_subcommand_parser(
    parser: argparse_flags.ArgumentParser) -> argparse._SubParsersAction:
  subparsers = parser.add_subparsers()
  (
    subparsers
    .add_parser('help', help='Show help message for a given command')
    .set_defaults(func=lambda _: parser.print_help())
  )
  init.add_parser(subparsers)
  (
    subparsers
    .add_parser('run', help='Runs a command')
    .set_defaults(func=_run_cmd)
  )
  stop.add_parser(subparsers)
  subscribe.add_parsers(subparsers)
  workspace_info.add_parser(subparsers)
  (
    subparsers
    .add_parser('version', help='Gets the version of the rx client')
    .set_defaults(func=_get_version)
  )
  return subparsers


def main(argv):
  logging.get_absl_handler().python_handler.use_absl_log_file(
    program_name='rx', log_dir=tempfile.gettempdir())

  parser = argparse_flags.ArgumentParser(
    description=(
      'rx is a cli interface for seamless hybrid development. Develop locally, '
      'then run locally or in the cloud.'))
  subparsers = get_subcommand_parser(parser)
  if len(argv) == 1:
    parser.print_help()
    return -1

  if argv[1] in subparsers.choices:
    ns, remainder = parser.parse_known_args(argv[1:])
    try:
      return ns.func(remainder)
    except KeyboardInterrupt:
      return worker_client.SIGINT_CODE
  else:
    # argparse doesn't like it when it doesn't recognize anything.
    return _run_cmd(argv[1:])


def run():
  app.run(main)

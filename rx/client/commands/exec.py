"""rx usage

To set up this directory on a remote host:

    rx init

You only have to run this once per directory, similar to `git init`.

To run a command on the remote host:

    rx CMD

Run 'rx --help' for more options or visit https://docs.run-rx.com.
"""
import argparse
import sys
import tempfile
from typing import List

from absl import app
from absl import flags
from absl import logging
from absl.flags import argparse_flags

from rx.client import worker_client
from rx.client.commands import init
from rx.client.commands import runner
from rx.client.commands import stop
from rx.client.commands import subscribe
from rx.client.commands import workspace_info
from rx.client.configuration import local


def _get_version(args: List[str]) -> int:
  del args
  print(local.VERSION)
  return 0


def get_subcommand_parser(
    parser: argparse_flags.ArgumentParser) -> argparse._SubParsersAction:
  subparsers = parser.add_subparsers()
  (
    subparsers
    .add_parser('help', help='Show help message for a given command')
    .set_defaults(func=lambda _: parser.print_help())
  )
  init.add_parser(subparsers)
  runner.add_parser(subparsers)
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
    return runner.RunCommand(argv[1:]).run()


def parse_flags_with_usage(args):
  try:
    return flags.FLAGS(args)
  except flags.Error as error:
    cmd = ' '.join(args[1:])
    print(
      f'{error}\n\nIf you are attempting to run a command on a remote machine, '
      f'try using quotes:\n\n\trx \'{cmd}\'')
    sys.exit(1)


# Run from rx.__main__.
def run():
  # Override absl's flag parser method with one that doesn't have a hard-coded
  # error message and then call sys.exit.
  app.run(main, flags_parser=parse_flags_with_usage)

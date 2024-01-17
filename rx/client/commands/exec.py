"""rx usage

To set up this directory on a remote host:

    rx init

You only have to run this once per directory, similar to `git init`.

To run a command on the remote host:

    rx CMD

Run 'rx --help' for more options or visit https://docs.run-rx.com.
"""
import argparse
import functools
import sys
import tempfile
from typing import List, Optional

from absl import app
from absl import logging
from absl.flags import argparse_flags

from rx.client import worker_client
from rx.client.commands import command
from rx.client.commands import init
from rx.client.commands import runner
from rx.client.commands import stop
from rx.client.commands import subscribe
from rx.client.commands import ws
from rx.client.configuration import local


class HelpCommand(command.Command):
  def __init__(
      self, parser: argparse.ArgumentParser, cmdline: command.CommandLine):
    self._parser = parser
    super().__init__(cmdline)

  def _run(self) -> int:
    self._parser.print_help()
    return 0


class VersionCommand(command.Command):
  def _run(self) -> int:
    print(local.VERSION)
    return 0


def get_subcommand_parser(
    parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
  subparsers = parser.add_subparsers(required=False)

  help_cmd = functools.partial(HelpCommand, parser)
  (
    subparsers
    .add_parser('help', help='Show help message for a given command')
    .set_defaults(cmd=help_cmd)
  )
  init.add_parser(subparsers)
  runner.add_parser(subparsers)
  stop.add_parser(subparsers)
  subscribe.add_parsers(subparsers)
  ws.add_parser(subparsers)
  (
    subparsers
    .add_parser('version', help='Gets the version of the rx client')
    .set_defaults(cmd=VersionCommand)
  )
  return subparsers


def main(cmdline: command.CommandLine):
  handler = logging.get_absl_handler()
  assert handler
  handler.python_handler.use_absl_log_file(
    program_name='rx', log_dir=tempfile.gettempdir())
  logging.info('Running "%s"', cmdline.original)

  try:
    cmd: command.Command = cmdline.ns.cmd(cmdline)
    cmd.run()
  except KeyboardInterrupt:
    return worker_client.SIGINT_CODE


def parse_flags_with_usage(argv) -> command.CommandLine:
  """The output of this is passed to main."""
  parser = argparse_flags.ArgumentParser(
    description=(
      'rx is a cli interface for seamless hybrid development. Develop locally, '
      'then run locally or in the cloud.'))
  subparsers = get_subcommand_parser(parser)

  if len(argv) == 1:
    parser.print_help()
    sys.exit(-1)

  # We want some behavior that argparse doesn't really support: implied "--"
  # and then consuming the rest of the arguments. Thus, find the first required
  # argument (one not prefixed with "-") and check if it's a subcommand. If it
  # is _not_, create a "run" command line manually and then handle parsing
  # normally.
  to_parse = argv[1:]  # Remove 'rx'
  cmd = get_first_required_arg(to_parse)
  if cmd not in subparsers.choices:
    to_parse = ['run'] + to_parse

  ns, remainder = parser.parse_known_args(to_parse)
  return command.CommandLine(
    ns=ns,
    remainder=remainder,
    original=argv,
  )


def get_first_required_arg(argv: List[str]) -> Optional[str]:
  """Gets the first arg not prefixed with '-'."""
  for arg in argv:
    if arg.startswith('-'):
      continue
    return arg
  return None


# Run from rx.__main__.
def run():
  # Override absl's flag parser method with one that doesn't have a hard-coded
  # error message and then call sys.exit.
  app.run(main, flags_parser=parse_flags_with_usage)

"""Rx usage

Configure this directory to be able to run on a remote host:

    rx init

You only have to run this once per directory, similar to `git init`.

To run a command on a configured remote host:

    rx CMD

"""
import pathlib
import tempfile
from typing import List

from absl import app
from absl import logging

from rx.client import executor
from rx.client import grpc_helper
from rx.client.commands import init
from rx.client.configuration import local
from rx.client.configuration import remote


class ExecCommand:

  def __init__(self, argv: List[str]):
    self._argv = argv
    self._config = local.find_local_config(pathlib.Path.cwd())

  def run(self) -> int:
    if self._config is None:
      print ('Run `rx init` first!')
      return -1
    remote_cfg = remote.Remote(self._config.cwd)
    with grpc_helper.get_channel(remote_cfg['grpc_addr']) as ch:
      client = executor.Client(ch, self._config, remote_cfg)
      return self._try_exec(client)

  def _try_exec(self, client: executor.Client) -> int:
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
      return client.exec(self._argv)
    except KeyboardInterrupt:
      client.maybe_kill()
      return executor.SIGINT_CODE


class VersionCommand:
  """Prints the version."""

  def run(self):
    print(local.VERSION)


def main(argv):
  logging.get_absl_handler().python_handler.use_absl_log_file(
    program_name='rx', log_dir=tempfile.gettempdir())
  if len(argv) == 1:
    app.usage(shorthelp=True)
    return -1
  cmd_to_run = argv[1]
  try:
    if cmd_to_run == 'init':
      cmd = init.InitCommand()
    elif cmd_to_run == 'version':
      cmd = VersionCommand()
    else:
      if cmd_to_run == 'run':
        # "rx run foo" is generally the same as "rx foo", but the extra "run" can
        # be handy when running a script called "init", say, on the remote
        # machine.
        argv = argv[1:]
      cmd = ExecCommand(argv[1:])
    return cmd.run()
  except KeyboardInterrupt:
    return executor.SIGINT_CODE


def run():
  app.run(main)

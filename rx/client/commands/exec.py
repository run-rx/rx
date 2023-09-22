"""rx usage

To set up this directory on a remote host:

    rx init

You only have to run this once per directory, similar to `git init`.

To run a command on the remote host:

    rx CMD

Run 'rx --help' for more options or visit https://www.run-rx.com.
"""
import tempfile
from typing import List

from absl import app
from absl import logging

from rx.client import worker_client
from rx.client import grpc_helper
from rx.client.commands import command
from rx.client.commands import init
from rx.client.commands import stop
from rx.client.commands import subscribe
from rx.client.configuration import config_base
from rx.client.configuration import local


class ExecCommand(command.Command):

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
      return client.exec(self._argv)
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


class VersionCommand:
  """Prints the version."""

  def run(self) -> int:
    print(local.VERSION)
    return 0


def main(argv):
  logging.get_absl_handler().python_handler.use_absl_log_file(
    program_name='rx', log_dir=tempfile.gettempdir())
  if len(argv) == 1:
    print('No command given.\n')
    app.usage(shorthelp=True)
    return -1
  cmd_to_run = argv[1]
  try:
    if cmd_to_run == 'init':
      cmd = init.InitCommand()
    elif cmd_to_run == 'stop':
      cmd = stop.StopCommand()
    elif cmd_to_run == 'subscribe':
      cmd = subscribe.SubscribeCommand()
    elif cmd_to_run == 'unsubscribe':
      cmd = subscribe.UnsubscribeCommand()
    elif cmd_to_run == 'version':
      cmd = VersionCommand()
    else:
      if cmd_to_run == 'run':
        # "rx run foo" is generally the same as "rx foo", but the extra "run"
        # can be handy when running a script called "init", say, on the remote
        # machine.
        argv = argv[1:]
      cmd = ExecCommand(argv[1:])
    return cmd.run()
  except KeyboardInterrupt:
    return worker_client.SIGINT_CODE


def run():
  app.run(main)

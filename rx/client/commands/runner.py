import argparse

from absl import logging

from rx.client import trex_client
from rx.client import worker_client
from rx.client import grpc_helper
from rx.client.commands import command
from rx.client.configuration import config_base


class RunCommand(command.Command):

  def __init__(self, cmdline: command.CommandLine):
    super().__init__(cmdline)
    self._argv = cmdline.remainder

  def _run(self) -> int:
    with grpc_helper.get_channel(self.remote_config.worker_addr) as ch:
      client = worker_client.create_authed_client(ch, self.local_config)
      return self._try_exec(client)

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
    except worker_client.RsyncError as e:
      # Fallthrough - retry
      logging.info('Rsync error: %s', e)
      pass
    except worker_client.WorkerError as e:
      print(e)
      return e.code

    # Fallthrough from retry.
    print('Error syncing code to your worker, checking with the scheduler...')
    return self.maybe_unfreeze()

  def maybe_unfreeze(self) -> int:
    # Connect to trex.
    with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
      cli = trex_client.create_authed_client(ch, self.local_config)
      try:
        result = cli.get_info(self.remote_config.workspace_id)
      except trex_client.TrexError as e:
        print(f'{e}, run `rx init` to get a new instance')
        return -1
      if result.state == 'frozen':
        result = cli.unfreeze(self.remote_config.workspace_id)
      else:
        print('Worker was unrechable, run `rx init` to get a new instance.')
        return -1
    if result.code == 0:
      print(
        'Done! Please rerun this command to use your newly restored workspace.')
    else:
      print(
        f'Error setting up this workspace on a new machine: {result.message}')
    return result.code


def add_parser(subparsers: argparse._SubParsersAction):
  (
    subparsers
    .add_parser('run', help='Runs a command')
    .set_defaults(cmd=RunCommand)
  )

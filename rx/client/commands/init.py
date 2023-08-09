import pathlib
import sys

from absl import flags
from absl import logging

from rx.client import grpc_helper
from rx.client import login
from rx.client import menu
from rx.client import trex_client
from rx.client import worker_client
from rx.client.commands import command
from rx.client.configuration import config_base
from rx.client.configuration import local

_DRY_RUN = flags.DEFINE_bool(
  'dry-run', False, 'Shows a list of files that would be uploaded by rx init')


class InitCommand(command.Command):
  """Initialize (or reinitialize) the remote."""

  def __init__(self):
    super().__init__()
    if self._rxroot:
      self._config_exists = local.get_local_config_path(self._rxroot).exists()
      self._user_info_exists = not login.needs_login(self._rxroot)
    else:
      # Fall back on using this dir for rxroot.
      self._rxroot = pathlib.Path.cwd()
      self._config_exists = False
      self._user_info_exists = False

  @property
  def rxroot(self) -> pathlib.Path:
    return self._rxroot

  def _show_init_message(self):
    steps = []
    if self._config_exists:
      reinit = menu.bool_prompt(
        'Looks like you already have an rx workspace. Would you like to stop '
        'that one\nand start a new one?', 'y')
      if not reinit:
        print('Okay, goodbye!')
        sys.exit(0)
      message = 'Got it. To re-init this workspace, rx will:\n\n'
      steps.append('Shut down your existing virtual machine.')
    else:
      message = 'To set up rx, this command will:\n\n'
    if not self._user_info_exists:
      steps.append(
        'Create an account for you with rx (or log you into your existing '
        'account).')
    steps.append('Set up a virtual machine on the cloud (on AWS).')
    steps.append(
      f'Copy over the files in this directory ({self._rxroot}) to your\n'
      '   virtual machine.')
    for num, step in enumerate(steps, 1):
      message += f'{num}. {step}\n'
    if not self._user_info_exists:
      message += (
        '\nWould you like to proceed with logging in/creating an rx account?')
    else:
      message += ('\nWould you like to proceed?')
    if not menu.bool_prompt(message, 'y'):
      print('Okay, goodbye!')
      sys.exit(0)

  def run(self) -> int:
    self._show_init_message()
    if self._config_exists:
      logging.info('Workspace already exists, resetting it.')
    try:
      config = local.create_local_config(self._rxroot)
      with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
        client = trex_client.Client(ch, config, auth_metadata=None)
        if _DRY_RUN.value:
          client.dry_run()
          return 0
        if not self._user_info_exists:
          ready_to_login = menu.bool_prompt(
            f"""
Great! First rx will need to open a browser window for you to log in. rx uses
Google's oauth to associate your email with your rx account.

Press y to continue:""", 'y')
          if not ready_to_login:
            print('Okay, goodbye!')
            return 0
        client.create_user_or_log_in()

        if not self._user_info_exists:
          prefix = 'Next,'
        else:
          prefix = 'Great! First'
        ready_to_upload = menu.bool_prompt(
          f"""
{prefix} rx is going to start a virtual machine in the cloud for your user.
This is your private machine and is currently free of charge (though limited in
resources).

The source code in this directory, will be copied to your virtual machine. To
check what will be uploaded, you can rerun this command with --dry-run and
modify .rxignore to exclude anything you don't want copied.

Are you sure you want to upload {self._rxroot} to the cloud?""", 'y')
        if not ready_to_upload:
          print('Okay, goodbye!')
          return 0
        if not menu._QUIET.value:
          print('Great! Let\'s get down to business.')
        return client.init()
    except trex_client.TrexError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return e.code
    except worker_client.UnreachableError as e:
      print(
        f'Worker {e.worker} was unrechable, run `rx init` to get a new '
        'instance.')
      return e.code

if __name__ == '__main__':
  print('Call exec.')

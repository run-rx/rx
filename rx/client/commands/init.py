import argparse
import pathlib
import sys

from absl import logging

from rx.client import grpc_helper
from rx.client import login
from rx.client import menu
from rx.client import trex_client
from rx.client.commands import command
from rx.client.configuration import config_base
from rx.client.configuration import local


class InitCommand(command.Command):
  """Initialize (or reinitialize) the remote."""

  def __init__(self, cmdline: command.CommandLine):
    super().__init__(cmdline)
    if self._rxroot:
      self._config_exists = local.get_local_config_path(self._rxroot).exists()
      self._user_info_exists = not login.needs_login(self._rxroot)
    else:
      # Fall back on using this dir for rxroot.
      self._rxroot = pathlib.Path.cwd()
      self._config_exists = False
      self._user_info_exists = False

  def _show_init_message(self):
    underline = '=' * len(str(self._rxroot))
    print(f"""
rx setup for {self._rxroot}
============={underline}
"""
)
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
      steps.append('Create your rx account (or log in).')
    steps.append('Set up a virtual machine on AWS.')
    steps.append(f'Copy the files in {self._rxroot} to your virtual machine.')
    for num, step in enumerate(steps, 1):
      message += f'{num}. {step}\n'
    message += ('\nWould you like to continue?')
    if not menu.bool_prompt(message, 'y'):
      print('Okay, goodbye!')
      sys.exit(0)

  def _set_up_user(
      self, client: trex_client.Client) -> bool:
    """Returns whether to continue."""
    if not self._user_info_exists:
      ready_to_login = menu.bool_prompt(
        f"""
First rx will need to open a browser window for you to log in. rx uses Google's
oauth to associate your email with your rx account.

Press y to continue:""", 'y')
      if not ready_to_login:
        print('Okay, goodbye!')
        return False
    client.create_user_or_log_in()
    return True

  def _run(self) -> int:
    self._show_init_message()
    if self._config_exists:
      logging.info('Workspace already exists, resetting it.')
    try:
      config = local.create_local_config(self._rxroot)
    except FileExistsError as e:
      print(e)
      return -1
    client = None
    try:
      with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
        client = trex_client.Client(ch, config, auth_metadata=None)
        if self._cmdline.ns.dry_run:
          client.dry_run()
          return 0

        cont = self._set_up_user(client)
        if not cont:
          return 0

        ready_to_upload = menu.bool_prompt(
          f"""
Upload your code
================

First rx is going to start a virtual machine in the cloud for your user. This is
your private machine and its state will be saved between commands.

The source code in this directory will be copied to your virtual machine. To
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

  def second_try(self, client: trex_client.Client) -> int:
    try:
      return client.init()
    except trex_client.TrexError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return e.code


def add_parser(subparsers: argparse._SubParsersAction):
  init_cmd = subparsers.add_parser(
    'init', help='Allocates and sets up a new workspace in AWS')
  init_cmd.add_argument(
    '--dry-run', default=False, dest='dry_run', action='store_true',
    help='Shows a list of files that would be uploaded by rx init')
  init_cmd.set_defaults(cmd=InitCommand)


if __name__ == '__main__':
  print('Call exec.')

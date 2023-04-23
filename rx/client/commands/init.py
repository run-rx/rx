import pathlib
import sys

from absl import logging

from rx.client import grpc_helper
from rx.client import init_client
from rx.client.configuration import config_base
from rx.client.configuration import local


class InitCommand:
  """Initialize (or reinitialize) the remote."""

  def __init__(self):
    self._cwd = pathlib.Path.cwd()
    self._config = local.find_local_config(self._cwd)

  def run(self) -> int:
    if self._config is None:
      local.install_local_files(self._cwd)
    else:
      logging.info('Workspace already exists, resetting it.')
    try:
      self._config = local.create_local_config(self._cwd)
      with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
        client = init_client.Client(ch, self._config)
        client.create_user_or_log_in()
        return client.init()
    except init_client.InitError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return e.code

if __name__ == '__main__':
  print('Call exec.')

import pathlib

from absl import logging

from rx.client.configuration import local
from rx.client import init_client


class InitCommand:
  """Initialize (or reinitialize) the remote."""

  def __init__(self):
    self._config = local.find_local_config(pathlib.Path.cwd())

  def run(self) -> int:
    if self._config is None:
      local.install_local_files(pathlib.Path.cwd())
      self._config = local.create_local_config()
    else:
      logging.info('Workspace already exists, resetting it.')
    client = init_client.Client(self._config)
    client.create_user_or_log_in()
    return client.init()


if __name__ == '__main__':
  print('Call exec.')

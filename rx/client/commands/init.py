import pathlib
import sys

from absl import flags
from absl import logging

from rx.client import grpc_helper
from rx.client import trex_client
from rx.client.configuration import config_base
from rx.client.configuration import local

_DRY_RUN = flags.DEFINE_bool(
  'dry-run', False, 'Shows a list of files that would be uploaded by rx init')


class InitCommand:
  """Initialize (or reinitialize) the remote."""

  def __init__(self):
    self._cwd = (
      pathlib.Path(config_base.RX_ROOT.value) if config_base.RX_ROOT.value else
      pathlib.Path.cwd())
    self._config = local.find_local_config(self._cwd)

  def run(self) -> int:
    if self._config is None:
      local.install_local_files(self._cwd)
    else:
      logging.info('Workspace already exists, resetting it.')
    try:
      self._config = local.create_local_config(self._cwd)
      with grpc_helper.get_channel(config_base.TREX_HOST.value) as ch:
        client = trex_client.Client(ch, self._config)
        if _DRY_RUN.value:
          client.dry_run()
          return 0
        client.create_user_or_log_in()
        return client.init()
    except trex_client.InitError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return e.code

if __name__ == '__main__':
  print('Call exec.')

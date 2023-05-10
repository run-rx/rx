import pathlib

from rx.client.configuration import config_base


class Remote(config_base.ReadOnlyConfig):
  def __init__(self, working_dir: pathlib.Path):
    super().__init__(_get_remote_config_file(working_dir))


class WritableRemote(config_base.ReadWriteConfig):
  def __init__(self, working_dir: pathlib.Path):
    super().__init__(_get_remote_config_file(working_dir))


def _get_remote_config_file(rxroot: pathlib.Path) -> pathlib.Path:
  return config_base.get_config_dir(rxroot) / 'remote'

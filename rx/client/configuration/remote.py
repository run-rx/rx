import pathlib

from rx.client.configuration import config_base


class Remote(config_base.ReadOnlyConfig):
  def __init__(self, working_dir: pathlib.Path):
    super().__init__(working_dir / _get_remote_config_file())


class WritableRemote(config_base.ReadWriteConfig):
  def __init__(self, working_dir: pathlib.Path):
    super().__init__(working_dir / _get_remote_config_file())


def _get_remote_config_file() -> pathlib.Path:
  return config_base.get_config_dir() / 'remote'

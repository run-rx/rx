from collections import abc
import pathlib
from types import TracebackType
from typing import Optional, Type

from absl import flags
import yaml

RX_DIR = pathlib.Path('.rx')

# Configuration files are placed under a directory with this name (this is just
# to make development easier, so we can have separate configs for
# local/dev/prod).
TREX_HOST = flags.DEFINE_string(
  'trex-host', 'trex.run-rx.com', 'GRPC host to connect to.')
RX_ROOT = flags.DEFINE_string(
  'rxroot', None, 'The directory to use as rxroot (defaults to pwd)')


class ReadOnlyConfig(abc.Mapping):
  def __init__(self, config_file: pathlib.Path, strict_mode: bool = True):
    self._config_file = config_file
    if config_file.exists():
      with self._config_file.open(mode='rt', encoding='utf-8') as fh:
        self._config = yaml.safe_load(fh)
    else:
      if strict_mode:
        raise ConfigNotFoundError(config_file)
      else:
        self._config = {}

  def __getitem__(self, item):
    assert item in self._config, (
      f'Could not access key {item} in {self._config_file}')
    return self._config[item]

  def __iter__(self):
    return self._config.__iter__()

  def __len__(self) -> int:
    return len(self._config)


class ReadWriteConfig(abc.MutableMapping, ReadOnlyConfig):

  def __init__(self, config_file: pathlib.Path):
    super().__init__(config_file, strict_mode=False)

  def __enter__(self):
    return self

  def __exit__(self, exctype: Optional[Type[BaseException]],
             excinst: Optional[BaseException],
             exctb: Optional[TracebackType]) -> bool:
    del excinst
    del exctb
    if exctype is None:
      # Keep config file up-to-date.
      with self._config_file.open(mode='wt', encoding='utf-8') as fh:
        yaml.safe_dump(self._config, fh)
    return False

  def __setitem__(self, item, value):
    self._config[item] = value

  def __delitem__(self, item):
    self._config.__delitem__(item)


def get_config_dir(rxroot: pathlib.Path) -> pathlib.Path:
  """Returns the absolute config directory path, e.g., /proj/.rx/t.c/config."""
  return rxroot / RX_DIR / TREX_HOST.value / 'config'


def is_local() -> bool:
  return TREX_HOST.value.startswith('localhost')


class ConfigNotFoundError(FileNotFoundError):
  def __init__(self, pth: pathlib.Path, *args: object) -> None:
    super().__init__(*args)
    self.path = pth

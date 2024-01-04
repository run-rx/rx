"""All of the info we can get without going to the server."""
import hashlib
import json
import pathlib
import os
import shutil
import subprocess
from typing import Optional, Tuple
import uuid

from absl import flags
from absl import logging
from google.protobuf import json_format
import sty
import yaml

from rx.client.configuration import config_base
from rx.proto import rx_pb2

VERSION = '0.0.15'

IGNORE = pathlib.Path('.rxignore')

_REMOTE = flags.DEFINE_string(
  'remote', None,
  'The path to the remote configuration file to use (see .rx/README.md).')
_RSYNC_PATH = flags.DEFINE_string('rsync_path', None, 'Path to rsync binary')

_REMOTE_DIR = config_base.RX_DIR / 'remotes'
_DEFAULT_REMOTE = _REMOTE_DIR / 'default'


class LocalConfigWriter(config_base.ReadWriteConfig):
  """This holds all of the configuration options that can be determined from
  the local machine."""

  def __init__(self, workspace_dir: pathlib.Path):
    super().__init__(get_local_config_path(workspace_dir))
    self._workspace_dir = workspace_dir

  def setup_remote(self):
    """Sets the "remote" field (and color) for the local config."""
    remote = str(_REMOTE.value if _REMOTE.value else _DEFAULT_REMOTE)
    self._config['remote'] = remote
    remote_path = self._workspace_dir / remote
    try:
      with remote_path.open(mode='rt', encoding='utf-8') as fh:
        remote_content = fh.read()
        self._set_color(remote_content)
    except FileExistsError:
      raise FileExistsError(
        f'Could not find remote config: {remote_path} does not exist')

  def _set_color(self, s: str):
    """Generate a random color based on the remote config."""
    h = hashlib.blake2s(digest_size=3)
    h.update(s.encode())
    hash_val = int(h.hexdigest(), 16)
    r = hash_val & 255
    hash_val = hash_val >> 8
    g = hash_val & 255
    hash_val = hash_val >> 8
    b = hash_val & 255
    self._config['color'] = {'r': r, 'g': g, 'b': b}


class LocalConfig(config_base.ReadOnlyConfig):
  """Create the local configuration."""

  def __init__(self, working_dir: pathlib.Path):
    super().__init__(get_local_config_path(working_dir))
    self._cwd = working_dir
    self.config_dir = self.cwd / config_base.RX_DIR
    self._color = None

  @property
  def cwd(self) -> pathlib.Path:
    return self._cwd

  @property
  def rsync_source(self) -> rx_pb2.RsyncSource:
    return rx_pb2.RsyncSource(
      machine_id=uuid.getnode(),
      directory=str(self.cwd),
    )

  def get_target_env(self) -> rx_pb2.Environment:
    remote_file = self.cwd / self._config['remote']
    try:
      with remote_file.open(mode='rt', encoding='utf-8') as fh:
        remote_config = yaml.safe_load(fh)
    except yaml.YAMLError as e:
      raise ConfigError(f'Could not parse yaml in {remote_file}: {e}')
    try:
      target_env = rx_pb2.Environment(**remote_config)
    except json_format.ParseError as e:
      raise ConfigError(f'Could not parse {self["remote"]}: {e}')
    return target_env

  def color_str(self, s: str) -> str:
    color = self._config['color']
    fg = sty.fg(color['r'], color['g'], color['b'])
    return f'{fg}{s}{sty.rs.fg}'


def create_local_config(rxroot: pathlib.Path) -> LocalConfig:
  """Gets or creates .rx directory."""
  _install_local_files(rxroot)
  config_dir = get_local_config_path(rxroot).parent
  config_dir.mkdir(exist_ok=True, parents=True)
  with LocalConfigWriter(rxroot) as c:
    c.setup_remote()
    c._config['project_name'] = _find_project_name(rxroot)
    c._config['rsync_path'] = _get_rsync_path()
  return LocalConfig(rxroot)


def find_rxroot(working_dir: pathlib.Path) -> Optional[pathlib.Path]:
  """Finds the rxroot, if it exists."""
  cfg_path = config_base.get_config_dir(working_dir)
  for parent in cfg_path.parents:
    if config_base.get_config_dir(parent).exists():
      return parent
  return None


def find_local_config(working_dir: pathlib.Path) -> Optional[LocalConfig]:
  """Factory to create a config by looking for .rx."""
  cfg_path = config_base.get_config_dir(working_dir)
  for parent in cfg_path.parents:
    if config_base.get_config_dir(parent).exists():
      return LocalConfig(parent)
  return None


def get_source_path() -> pathlib.Path:
  """Gets the path bundled client files can be found on."""
  # __file__ is ./rx/client/configuration/local.py, so this resolves to ./.
  return pathlib.Path(__file__).resolve().parent.parent.parent.parent


def get_grpc_metadata() -> Tuple[Tuple[str, str]]:
  return (('cv', VERSION),)


def _install_local_files(rxroot: pathlib.Path):
  install_dir = pathlib.Path(get_source_path() / 'install')

  _install_file(install_dir, rxroot, IGNORE)

  config_dir = rxroot / config_base.RX_DIR
  config_dir.mkdir(exist_ok=True, parents=True)
  _install_file(install_dir, config_dir, 'README.md')

  remotes = rxroot / _REMOTE_DIR
  remotes.mkdir(exist_ok=True, parents=True)

  # Copy built-in configs.
  python_cpu = _install_file(install_dir, remotes, 'python-cpu.yaml')
  _install_file(install_dir, remotes, 'python-gpu.yaml')
  # Create soft link.
  default_config = remotes / 'default'
  default_target = str(default_config.resolve())
  is_yaml = (
    default_target.endswith('.yaml') or
    default_target.endswith('.yml'))
  if default_config.exists():
    if is_yaml:
      # Don't undo someone else's config, unless it's old.
      return
    print(
      f'Your default config points to {default_target}, which doesn\'t look '
      f'like a yaml file. Updating it to {python_cpu}.')
    default_config.unlink()
  # .rx/remote/default -> python-cpu.yaml
  default_config.symlink_to('python-cpu.yaml')


def _get_rsync_path() -> str:
  """Make sure rsync is installed."""
  if _RSYNC_PATH.value:
    return _RSYNC_PATH.value
  try:
    result = subprocess.run(
      ['which', 'rsync'], check=True, capture_output=True)
  except subprocess.CalledProcessError as e:
    logging.error('Error finding rsync: %s', e)
    raise ConfigError('Cannot find rsync, is it installed/on your path?')
  # Use rsync on PATH
  return result.stdout.decode('utf-8').strip('\n')


def _find_project_name(start_dir: pathlib.Path) -> str:
  """Heuristic to find a reasonable name for this project."""
  # Probably the git repo is rooted on a good name.
  if (start_dir / '.git').exists():
    return start_dir.name
  for parent in start_dir.parents:
    if (parent / '.git').exists():
      return start_dir.name
  # Maybe we haven't initialized git yet, use out name.
  return start_dir.name


def get_local_config_path(rxroot: pathlib.Path) -> pathlib.Path:
  """Return .rx/trex-dev.run-rx.com/config/local."""
  return config_base.get_config_dir(rxroot) / 'local'


def _install_file(install_dir, config_dir, base_name) -> pathlib.Path:
  """Installs a file if it doesn't already exist."""
  source_path = install_dir / base_name
  destination_path = config_dir / base_name
  if not destination_path.exists():
    shutil.copy(source_path, destination_path)
  return destination_path


class ConfigError(RuntimeError):
  pass

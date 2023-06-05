"""All of the info we can get without going to the server."""
import hashlib
import json
import pathlib
import shutil
import subprocess
from typing import Optional, Tuple
import uuid

from absl import flags
from absl import logging
import sty

from rx.client.configuration import config_base
from rx.proto import rx_pb2

VERSION = '0.0.5'

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
    super().__init__(_get_local_config_file(workspace_dir))
    self._workspace_dir = workspace_dir

  def setup_remote(self):
    """Sets the "remote" field (and color) for the local config."""
    remote = str(_REMOTE.value if _REMOTE.value else _DEFAULT_REMOTE)
    remote_path = self._workspace_dir / remote
    try:
      with remote_path.open(mode='rt', encoding='utf-8') as fh:
        remote_content = fh.read()
        self._set_color(remote_content)
        self['remote'] = remote
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
    self['color'] = {'r': r, 'g': g, 'b': b}


class LocalConfig(config_base.ReadOnlyConfig):
  """Create the local configuration."""

  def __init__(self, working_dir: pathlib.Path):
    super().__init__(_get_local_config_file(working_dir))
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

  def _get_source_env(self, docker_image: str) -> rx_pb2.Environment:
    # TODO: how to automatically determine language?
    if 'python' not in docker_image:
      logging.info('Using a non-Python image. There be dragons here.')
      return rx_pb2.Environment()
    return rx_pb2.Environment(python=rx_pb2.Python())

  def get_target_env(self) -> rx_pb2.Environment:
    remote_file = self.cwd / self['remote']
    try:
      with remote_file.open(mode='rt', encoding='utf-8') as fh:
        remote_config = json.load(fh)
    except json.JSONDecodeError as e:
      logging.exception(f'Could not parse {self["remote"]}')
      raise e
    env = rx_pb2.Environment(alloc=rx_pb2.Remote())
    if 'image' not in remote_config or 'docker' not in remote_config['image']:
      raise ConfigError(
        f'Remote config {self["remote"]} must contain "image": '
        '{"docker": "<docker image>"}')
    docker_image = remote_config['image']['docker']
    env.alloc.image.CopyFrom(rx_pb2.Remote.Image(
      docker=docker_image,
    ))
    if 'hardware' in remote_config and 'processor' in remote_config['hardware']:
      env.alloc.hardware.CopyFrom(rx_pb2.Remote.Hardware(
        processor=remote_config['hardware']['processor']
      ))
    env.MergeFrom(self._get_source_env(docker_image))
    return env

  def color_str(self, s: str) -> str:
    color = self['color']
    fg = sty.fg(color['r'], color['g'], color['b'])
    return f'{fg}{s}{sty.rs.fg}'


def create_local_config(cwd: pathlib.Path) -> LocalConfig:
  """Gets or creates .rx directory."""
  config_dir = _get_local_config_file(cwd).parent
  config_dir.mkdir(exist_ok=True, parents=True)
  with LocalConfigWriter(cwd) as c:
    c.setup_remote()
    c['project_name'] = _find_project_name(cwd)
    c['rsync_path'] = _get_rsync_path()
  return LocalConfig(cwd)


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


def install_local_files(cwd: pathlib.Path):
  # Output directory.
  (cwd / 'rx-out').mkdir(exist_ok=True)

  install_dir = pathlib.Path(get_source_path() / 'install')

  _install_file(install_dir, cwd, IGNORE)

  config_dir = cwd / config_base.RX_DIR
  config_dir.mkdir(exist_ok=True, parents=True)
  _install_file(install_dir, config_dir, 'README.md')

  remotes = cwd / _REMOTE_DIR
  remotes.mkdir(exist_ok=True, parents=True)

  # Copy built-in configs.
  _install_file(install_dir, remotes, 'python-cpu')
  _install_file(install_dir, remotes, 'python-gpu')
  # Create soft link.
  default_config = remotes / 'default'
  if default_config.exists():
    # Don't undo someone else's config.
    return
  # .rx/remote/default -> python-cpu
  default_config.symlink_to('python-cpu')


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


def _get_local_config_file(rxroot: pathlib.Path) -> pathlib.Path:
  """Return .rx/trex-dev.run-rx.com/config/local."""
  return config_base.get_config_dir(rxroot) / 'local'


def _install_file(install_dir, config_dir, base_name):
  """Installs a file if it doesn't already exist."""
  source_path = install_dir / base_name
  destination_path = config_dir / base_name
  if not destination_path.exists():
    shutil.copy(source_path, destination_path)


class ConfigError(RuntimeError):
  pass

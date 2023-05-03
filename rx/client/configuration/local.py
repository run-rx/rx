"""All of the info we can get without going to the server."""
import hashlib
import json
import pathlib
import shutil
import sys
from typing import Optional, Tuple
import uuid

from absl import flags
from absl import logging
import sty

from rx.client.configuration import config_base
from rx.proto import rx_pb2

CLIENT_VERSION = '0.0.1'

IGNORE = pathlib.Path('.rxignore')

_REMOTE = flags.DEFINE_string(
  'remote', 'default',
  'The remote configuration file to use (see .rx/README.md).')

_REMOTE_DIR = config_base.RX_DIR / 'remotes'


class LocalConfigWriter(config_base.ReadWriteConfig):
  """This holds all of the configuration options that can be determined from
  the local machine."""

  def __init__(self, workspace_dir: pathlib.Path):
    super().__init__(workspace_dir / _get_local_config_file())
    self._workspace_dir = workspace_dir

  def setup_remote(self):
    """Sets the "remote" field (and color) for the local config."""
    remote = _REMOTE.value
    remote_path = self._workspace_dir / _REMOTE_DIR / remote
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
    super().__init__(working_dir / _get_local_config_file())
    self.cwd = working_dir
    self.config_dir = self.cwd / config_base.RX_DIR
    self._color = None

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
    remote_file = self.cwd / _REMOTE_DIR / self['remote']
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
  config_dir = (cwd / _get_local_config_file()).parent
  config_dir.mkdir(exist_ok=True, parents=True)
  with LocalConfigWriter(cwd) as c:
    c.setup_remote()
    c['project_name'] = _find_project_name(cwd)
  return LocalConfig(cwd)


def find_local_config(working_dir: pathlib.Path) -> Optional[LocalConfig]:
  """Factory to create a config by looking for .rx."""
  cfg_path = working_dir / config_base.get_config_dir()
  for parent in cfg_path.parents:
    if (parent / config_base.get_config_dir()).exists():
      return LocalConfig(parent)
  return None


def get_bundle_path() -> pathlib.Path:
  """Gets the path bundled client files can be found on."""
  if is_bundled():
    return pathlib.Path(sys._MEIPASS)
  else:
    # We are running in a normal Python environment.
    # __file__ is ./rx/client/configuration/local.py, so this resolves to ./.
    return pathlib.Path(__file__).resolve().parent.parent.parent.parent


def get_grpc_metadata() -> Tuple[Tuple[str, str]]:
  return (('cv', CLIENT_VERSION),)


def install_local_files(cwd: pathlib.Path):
  # Output directory.
  (cwd / 'rx-out').mkdir(exist_ok=True)

  install_dir = pathlib.Path(get_bundle_path() / 'install')

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


def is_bundled() -> bool:
  """If this is bundled rx (vs. running from source)."""
  return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


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


def _get_local_config_file() -> pathlib.Path:
  """Return .rx/trex-dev.run-rx.com/config/local."""
  return config_base.get_config_dir() / 'local'


def _install_file(install_dir, config_dir, base_name):
  """Installs a file if it doesn't already exist."""
  source_path = install_dir / base_name
  destination_path = config_dir / base_name
  if not destination_path.exists():
    shutil.copy(source_path, destination_path)


class ConfigError(RuntimeError):
  pass

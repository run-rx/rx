"""All of the info we can get without going to the server."""
import dataclasses
import pathlib
import shutil
import subprocess
from typing import Any, Dict, Optional, Tuple
import uuid

from absl import flags
from absl import logging
import yaml

from rx.client.configuration import config_base
from rx.proto import rx_pb2

VERSION = '0.0.18'

IGNORE = pathlib.Path('.rxignore')
REMOTE_DIR = config_base.RX_DIR / 'remotes'

_REMOTE = flags.DEFINE_string(
  'remote', None,
  'The path to the remote configuration file to use (see .rx/README.md).')
_RSYNC_PATH = flags.DEFINE_string('rsync_path', None, 'Path to rsync binary')

_DEFAULT_REMOTE = REMOTE_DIR / 'default'


@dataclasses.dataclass(frozen=True)
class LocalConfig:
  """Create the local configuration."""
  cwd: pathlib.Path
  remote: str
  project_name: str
  rsync_path: str
  should_sync: bool

  @property
  def rsync_source(self) -> rx_pb2.RsyncSource:
    return rx_pb2.RsyncSource(
      machine_id=uuid.getnode(),
      directory=str(self.cwd),
    )

  def get_target_env(self) -> rx_pb2.Environment:
    remote_file: pathlib.Path = self.cwd / self.remote
    if not remote_file.exists():
      return rx_pb2.Environment()
    try:
      with remote_file.open(mode='rt', encoding='utf-8') as fh:
        remote_config = yaml.safe_load(fh)
    except yaml.YAMLError as e:
      raise ConfigError(f'Could not parse yaml in {remote_file}: {e}')
    return env_dict_to_pb(remote_config)

  def store(self):
    cfg_file = get_local_config_path(self.cwd)
    with cfg_file.open(mode='wt', encoding='utf-8') as fh:
      yaml.safe_dump({
        'remote': self.remote,
        'project_name': self.project_name,
        'rsync_path': self.rsync_path,
        'should_sync': self.should_sync
      }, fh)


def create_local_config(rxroot: pathlib.Path, should_sync: bool) -> LocalConfig:
  """Gets or creates .rx directory and local config."""
  config_dir = get_local_config_path(rxroot).parent
  _install_rxignore(rxroot)
  config_dir.mkdir(exist_ok=True, parents=True)
  cfg = LocalConfig(
    cwd=rxroot,
    remote=str(_REMOTE.value if _REMOTE.value else _DEFAULT_REMOTE),
    project_name=_find_project_name(rxroot),
    rsync_path=_get_rsync_path(),
    should_sync=should_sync,
  )
  cfg.store()
  return cfg


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
      return load_config(parent)
  return None


def get_source_path() -> pathlib.Path:
  """Gets the path bundled client files can be found on."""
  # __file__ is ./rx/client/configuration/local.py, so this resolves to ./.
  return pathlib.Path(__file__).resolve().parent.parent.parent.parent


def get_grpc_metadata() -> Tuple[Tuple[str, str]]:
  return (('cv', VERSION),)


def env_dict_to_pb(env_dict: Optional[Dict[str, Any]]) -> rx_pb2.Environment:
  env_pb = rx_pb2.Environment()
  if not env_dict:
    # Empty config comes in as None.
    return env_pb
  if 'remote' in env_dict:
    remote_dict = env_dict['remote']
    remote_pb = rx_pb2.Remote()
    if 'hardware' in remote_dict:
      remote_pb.hardware.CopyFrom(rx_pb2.Hardware(**remote_dict['hardware']))
    if 'toolchain' in remote_dict:
      for tool in remote_dict['toolchain']:
        remote_pb.toolchain.append(rx_pb2.Tool(**tool))
    env_pb.remote.CopyFrom(remote_pb)
  if 'image' in env_dict:
    image_dict = env_dict['image']
    image_pb = rx_pb2.Image()
    if 'registry' in image_dict:
      image_pb.registry = image_dict['registry']
    if 'repository' in image_dict:
      image_pb.repository = image_dict['repository']
    if 'tag' in image_dict:
      image_pb.tag = image_dict['tag']
    if 'environment_variables' in image_dict:
      for k, v in image_dict['environment_variables'].items():
        if isinstance(v, bool):
          # YAML is a bit too helpful about type conversions.
          v = 'true' if v else 'false'
        image_pb.environment_variables[k] = str(v)
    if 'ports' in image_dict:
      image_pb.ports.extend(image_dict['ports'])
    env_pb.image.CopyFrom(image_pb)
  return env_pb


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


def _install_rxignore(rxroot: pathlib.Path):
  source_path = get_source_path() / 'install' / IGNORE
  destination_path = rxroot / IGNORE
  if not destination_path.exists():
    shutil.copy(source_path, destination_path)


def load_config(rxroot: pathlib.Path) -> LocalConfig:
  cfg_path = get_local_config_path(rxroot)
  if not cfg_path.exists():
    raise config_base.ConfigNotFoundError(cfg_path)
  try:
    with cfg_path.open(mode='rt', encoding='utf-8') as fh:
      cfg = yaml.safe_load(fh)
  except yaml.YAMLError as e:
    raise ConfigError(f'Could not parse yaml in {cfg_path}: {e}')
  cfg['cwd'] = rxroot
  return LocalConfig(**cfg)


def get_local_config_path(rxroot: pathlib.Path) -> pathlib.Path:
  """Return .rx/trex-dev.run-rx.com/config/local."""
  return config_base.get_config_dir(rxroot) / 'local'


class ConfigError(RuntimeError):
  pass

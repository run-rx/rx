"""All of the info we can get without going to the server."""
import pathlib
import subprocess
from typing import Any, Dict, Optional, Tuple
import uuid

from absl import flags
from absl import logging
import yaml

from rx.client.configuration import config_base
from rx.proto import rx_pb2

VERSION = '0.0.17'

IGNORE = pathlib.Path('.rxignore')
REMOTE_DIR = config_base.RX_DIR / 'remotes'

_REMOTE = flags.DEFINE_string(
  'remote', None,
  'The path to the remote configuration file to use (see .rx/README.md).')
_RSYNC_PATH = flags.DEFINE_string('rsync_path', None, 'Path to rsync binary')

_DEFAULT_REMOTE = REMOTE_DIR / 'default'


class LocalConfigWriter(config_base.ReadWriteConfig):
  """This holds all of the configuration options that can be determined from
  the local machine."""

  def __init__(self, workspace_dir: pathlib.Path):
    super().__init__(get_local_config_path(workspace_dir))
    self._workspace_dir = workspace_dir

  def setup_remote(self):
    """Sets the "remote" field for the local config."""
    remote = str(_REMOTE.value if _REMOTE.value else _DEFAULT_REMOTE)
    self._config['remote'] = remote


class LocalConfig(config_base.ReadOnlyConfig):
  """Create the local configuration."""

  def __init__(self, working_dir: pathlib.Path):
    super().__init__(get_local_config_path(working_dir))
    self._cwd = working_dir
    self.config_dir = self.cwd / config_base.RX_DIR

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
    remote_file: pathlib.Path = self.cwd / self._config['remote']
    if not remote_file.exists():
      return rx_pb2.Environment()
    try:
      with remote_file.open(mode='rt', encoding='utf-8') as fh:
        remote_config = yaml.safe_load(fh)
    except yaml.YAMLError as e:
      raise ConfigError(f'Could not parse yaml in {remote_file}: {e}')
    return env_dict_to_pb(remote_config)


def create_local_config(rxroot: pathlib.Path) -> LocalConfig:
  """Gets or creates .rx directory."""
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


def env_dict_to_pb(env_dict: Optional[Dict[str, Any]]) -> rx_pb2.Environment:
  env_pb = rx_pb2.Environment()
  if not env_dict:
    # Empty config comes in as None.
    return env_pb
  if 'remote' in env_dict:
    remote_pb = rx_pb2.Remote(**env_dict['remote'])
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


def get_local_config_path(rxroot: pathlib.Path) -> pathlib.Path:
  """Return .rx/trex-dev.run-rx.com/config/local."""
  return config_base.get_config_dir(rxroot) / 'local'


class ConfigError(RuntimeError):
  pass

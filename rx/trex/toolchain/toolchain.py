import datetime
from typing import Optional

from absl import logging
from google.protobuf import json_format
import yaml

from rx.client.configuration import local
from rx.proto import rx_pb2


class Toolchain:
  def __init__(self, local_cfg: local.LocalConfig) -> None:
    self._local_cfg = local_cfg

  def save_config(self, config: rx_pb2.Environment) -> Optional[str]:
    starting_config = (
      self._local_cfg.get_target_env().SerializeToString(deterministic=True))
    ending_config = config.SerializeToString(deterministic=True)
    if starting_config == ending_config:
      logging.info('Start and end remote configs are the same, not saving.')
      return None

    config_str = yaml.safe_dump(
      json_format.MessageToDict(
        config,
        preserving_proto_field_name=True,
      )
    )
    config_file = self._write_config(config_str, config.image.repository)
    logging.info('Config written to %s', config_file)
    return config_file

  def _write_config(self, config: str, config_name: str) -> str:
    remotes = self._local_cfg.cwd / local.REMOTE_DIR
    remotes.mkdir(exist_ok=True, parents=True)

    datestr = datetime.date.today().strftime('%Y%m%d')
    config_name = config_name.replace('/', '-')
    config_file = remotes / f'{config_name}-{datestr}.yaml'
    # This could overlap with an existing config file which is okay. Just
    # overwrite.
    with config_file.open(mode='wt', encoding='utf-8') as fh:
      fh.write(config)

    # Create soft link.
    default_config = remotes / 'default'
    if not default_config.exists():
      # If it's a symlink pointing to a non-existent file.
      if default_config.is_symlink():
        default_config.unlink()
      # .rx/remote/default -> python-cpu.yaml
      default_config.symlink_to(config_file)

    return str(config_file.relative_to(self._local_cfg.cwd))


class ToolchainError(RuntimeError):
  pass

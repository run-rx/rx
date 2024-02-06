import datetime
from typing import List

from absl import logging
from google.protobuf import json_format
import yaml

from rx.client.configuration import local
from rx.proto import rx_pb2
from rx.proto import trex_pb2
from rx.trex.toolchain import lang_detector
from rx.trex.toolchain import local_fs
from rx.trex.toolchain import manifest


class Toolchain:
  def __init__(
      self,
      local_cfg: local.LocalConfig,
      provided_config: rx_pb2.Environment,
  ) -> None:
    self._local_cfg = local_cfg
    self._provided_config = provided_config

  @property
  def has_toolchain(self) -> bool:
    return (
      self._provided_config.HasField('image') and
      bool(self._provided_config.image.repository))

  def get_toolchain(self) -> List[trex_pb2.Tool]:
    try:
      m = manifest.Manifest(local_fs.get_manifest(self._local_cfg))
      d = lang_detector.Detector(m)
      return [trex_pb2.Tool(name=t.name) for t in d.get_languages()]
    except local_fs.ManifestError as e:
      raise ToolchainError(e)

  def print_config(self, gc: rx_pb2.GeneratedConfig):
    if gc.unrecognized_tools:
      logging.info(
        'Ignoring tools %s', ', '.join(x.name for x in gc.unrecognized_tools))
    config = yaml.safe_dump(json_format.MessageToDict(gc.config))
    config_file = self._write_config(config, gc.human_env_name)
    if gc.image_decision == 'fallback':
      print('Could not determine project environment, using fallback image:\n')
    else:
      print('Automatically generated the following environment:\n')
    print(f'{config}\nWritten to {config_file}\n')

  def _write_config(self, config: str, config_name: str) -> str:
    remotes = self._local_cfg.cwd / local.REMOTE_DIR
    remotes.mkdir(exist_ok=True, parents=True)

    datestr = datetime.date.today().strftime('%Y%m%d')
    config_file = remotes / f'{config_name}-{datestr}.yaml'
    # This could overlap with an existing config file which is okay. Just
    # overwrite.
    with config_file.open(mode='wt', encoding='utf-8') as fh:
      fh.write(config)

    # Create soft link.
    default_config = remotes / 'default'
    if default_config.is_symlink():
      default_config.unlink()
    # .rx/remote/default -> python-cpu.yaml
    default_config.symlink_to(config_file)

    return str(config_file.relative_to(self._local_cfg.cwd))


class ToolchainError(RuntimeError):
  pass

import pathlib

from rx.client.configuration import config_base
from rx.client.configuration import local
from rx.client.configuration import remote

class Command:
  def __init__(self) -> None:
    if config_base.RX_ROOT.value:
      self._rxroot = pathlib.Path(config_base.RX_ROOT.value)
    else:
      self._rxroot = local.find_rxroot(pathlib.Path.cwd())

  @property
  def local_config(self) -> local.LocalConfig:
    if not self._rxroot:
      raise config_base.ConfigNotFoundError(
        pathlib.Path('.'), 'Run `rx init` first!')
    config = local.find_local_config(self._rxroot)
    if not config:
      raise config_base.ConfigNotFoundError(
        self._rxroot, 'Run `rx init` first!')
    return config

  @property
  def remote_config(self) -> remote.Remote:
    return remote.Remote(self.local_config.cwd)

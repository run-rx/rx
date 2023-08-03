import pathlib

from rx.client.configuration import config_base
from rx.client.configuration import local

class Command:
  def __init__(self) -> None:
    if config_base.RX_ROOT.value:
      self._rxroot = pathlib.Path(config_base.RX_ROOT.value)
    else:
      self._rxroot = local.find_rxroot(pathlib.Path.cwd())

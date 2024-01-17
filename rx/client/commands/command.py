import argparse
import dataclasses
import pathlib
import sys
from typing import List

from rx.client import trex_client
from rx.client.configuration import config_base
from rx.client.configuration import local
from rx.client.configuration import remote


@dataclasses.dataclass(frozen=True)
class CommandLine:
  ns: argparse.Namespace
  remainder: List[str]
  original: List[str]


class Command:
  def __init__(self, cmdline: CommandLine) -> None:
    self._cmdline = cmdline
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

  def run(self) -> int:
    try:
      return self._run()
    except config_base.ConfigNotFoundError as e:
      path = 'cwd' if e.path == '.' else e.path
      print(
        f'No workspace found at {path}, {e}.', file=sys.stderr, flush=True)
      return -1

  def _run(self) -> int:
    raise NotImplementedError()


class TrexCommand(Command):
  def run(self) -> int:
    try:
      return super().run()
    except trex_client.TrexError as e:
      print(e, file=sys.stderr, flush=True)
      return e.code

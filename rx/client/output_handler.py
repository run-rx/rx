"""Handle outputs from the server."""
import pathlib
from typing import Set

from rx.client.worker import rsync
from rx.proto import rx_pb2


class OutputHandler:
  """Handle output files and stdout/err."""

  def __init__(self, rxroot: pathlib.Path) -> None:
    self._rxroot = rxroot
    self._current_outputs: Set[pathlib.Path] = set()

  def handle(self, resp: rx_pb2.ExecResponse):
    """Creates output files."""
    for pth_str in resp.output_files:
      self._current_outputs.add(pathlib.Path(pth_str))

  def write_outputs(self, rsync_client: rsync.RsyncClient):
    if not self._current_outputs:
      return
    rsync_client.from_remote('.', self._rxroot)
    print('Changed:')
    for pth in sorted(self._current_outputs):
      print(f'  {pth}')

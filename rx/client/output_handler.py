"""Handle outputs from the server."""
import pathlib
import sys
from typing import List

from rx.client.worker import rsync
from rx.proto import rx_pb2


class OutputHandler:
  """Handle output files and stdout/err."""

  def __init__(self, rxroot: pathlib.Path) -> None:
    self._rxroot = rxroot
    self._current_outputs = set()

  @property
  def remote_paths(self) -> List[str]:
    return sorted([f'{o}' for o in self._current_outputs])

  def handle(self, resp: rx_pb2.ExecResponse):
    """Shows output & error streams and creates output files."""
    if resp.stdout:
      sys.stdout.buffer.write(resp.stdout)
      sys.stdout.flush()
    if resp.stderr:
      sys.stderr.buffer.write(resp.stderr)
      sys.stderr.flush()
    for pth_str in resp.output_files:
      self._current_outputs.add(pathlib.Path(pth_str))

  def write_outputs(self, rsync_client: rsync.RsyncClient):
    if not self._current_outputs:
      return
    rsync_client.from_remote('rx-out', self._rxroot / pathlib.Path('rx-out'))
    print('Created outputs:')
    for pth in self.remote_paths:
      print(f'  {pth}')

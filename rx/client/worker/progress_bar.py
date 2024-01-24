from typing import Iterable, Optional, cast

import grpc
import tqdm

from rx.proto import rx_pb2


def show_progress_bars(
    it: Iterable[rx_pb2.DockerImageProgress]) -> Optional[rx_pb2.Result]:
  progress_bars = {}
  try:
    for pp in it:
      if pp.id not in progress_bars:
        # First item must have a total.
        if pp.total == 0:
          continue
        progress_bars[pp.id] = ProgressBar(pp)
      progress_bars[pp.id].update(pp)
  except grpc.RpcError as e:
    e = cast(grpc.Call, e)
    return rx_pb2.Result(code=rx_pb2.UNKNOWN, message=e.details())
  finally:
    for p in progress_bars.values():
      p.close()


class ProgressBar:

  def __init__(self, pp: rx_pb2.DockerImageProgress) -> None:
    assert pp.total > 0
    self._bar = tqdm.tqdm(
      desc=f'{pp.status} layer {pp.id}',
      total=pp.total,
      unit=' bytes',
      unit_scale=True,
      bar_format='{l_bar}{bar:10}{r_bar}{bar:-10b}')
    self._is_done = False

  def close(self):
    self._bar.close()

  def update(self, pp: rx_pb2.DockerImageProgress):
    if pp.total == 0:
      self._bar.set_description(f'{pp.status} layer {pp.id}')
      return
    if self._is_done:
      return

    # Note: this jumps back to 0 for download -> extract, which is good?
    self._bar.update(pp.current - self._bar.n)
    if self._bar.n == pp.total:
      self._is_done = True

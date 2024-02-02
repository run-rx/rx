"""Tools for processing the project's file list."""
import collections
import os
from typing import Iterator, List


class Manifest:
  """Represents files in a user's project."""

  def __init__(self, manifest: List[str]) -> None:
    self._manifest = manifest
    self._counts = collections.defaultdict(lambda: 0)
    self._processed = False

  def _process(self):
    """Initially populate _counts."""
    self._processed = True
    for f in self._manifest:
      _, ext = os.path.splitext(f)
      # E.g., {'.go': 4}
      self._counts[ext] += 1

  def most_popular_extensions(self) -> Iterator[str]:
    """Returns the extension on the most files."""
    if not self._processed:
      self._process()
    for k, _ in sorted(self._counts.items(), key=lambda x: x[1], reverse=True):
      yield k

  def __contains__(self, fullpath: str) -> bool:
    """Returns if the given path is in the manifest."""
    if not self._processed:
      self._process()
    return fullpath in self._manifest

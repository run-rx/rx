"""This detects what languages a project is using."""
import dataclasses
from typing import List

from rx.trex.toolchain import manifest

_KNOWN_EXTENSION = {
  '.c': 'c',
  '.cc': 'cpp',
  '.go': 'golang',
  '.java': 'java',
  '.js': 'node',
  '.jsx': 'node',
  '.php': 'php',
  '.py': 'python',
  '.rs': 'rust',
  '.ts': 'node',
  '.tsx': 'node',
}


@dataclasses.dataclass(frozen=True)
class DetectedTool:
  name: str
  why: str = dataclasses.field(hash=False, compare=False)


class Detector:
  """Detects which language a repo is likely primarily using."""
  def __init__(self, m: manifest.Manifest) -> None:
    self._manifest = m

  def get_languages(self) -> List[DetectedTool]:
    """Returns the likely languages/tools for the project."""
    detected = set()
    why = 'package manager'
    if (
      'environment.yaml' in self._manifest or
      'environment.yml' in self._manifest):
      detected.add(DetectedTool(name='conda', why=why))
    if 'requirements.txt' in self._manifest:
      detected.add(DetectedTool(name='pip', why=why))
    if 'pom.xml' in self._manifest:
      detected.add(DetectedTool(name='maven', why=why))
    if 'package.json' in self._manifest:
      detected.add(DetectedTool(name='node', why=why))
    if 'Cargo.toml' in self._manifest:
      detected.add(DetectedTool(name='rust', why=why))

    # We could not find a language via package manager options. Look for
    # suffixes.
    why = 'file extension'
    for lang in self._manifest.most_popular_extensions():
      if lang in _KNOWN_EXTENSION:
        detected.add(DetectedTool(name=_KNOWN_EXTENSION[lang], why=why))

    return list(detected)

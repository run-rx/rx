"""This detects what languages a project is using."""
from rx.trex.toolchain import manifest

_KNOWN_EXTENSION = {
  '.c': 'c',
  '.cc': 'cpp',
  '.go': 'go',
  '.java': 'java',
  '.js': 'node',
  '.jsx': 'node',
  '.php': 'php',
  '.py': 'python',
  '.rs': 'rust',
  '.ts': 'node',
  '.tsx': 'node',
}


class Detector:
  """Detects which language a repo is likely primarily using."""
  def __init__(self, m: manifest.Manifest) -> None:
    self._manifest = m
    self._why = None

  def get_language(self) -> str:
    """Returns the likely language for the project."""
    self._why = 'package manager'
    if (
      'environment.yaml' in self._manifest or
      'environment.yml' in self._manifest):
      return 'conda'
    if 'requirements.txt' in self._manifest:
      return 'python'
    if 'pom.xml' in self._manifest:
      return 'maven'
    if 'package.json' in self._manifest:
      return 'node'
    if 'Cargo.toml' in self._manifest:
      return 'rust'

    # We could not find a language via package manager options. Look for
    # suffixes.
    self._why = 'file extensions'
    for lang in self._manifest.most_popular_extensions():
      if lang in _KNOWN_EXTENSION:
        return _KNOWN_EXTENSION[lang]

    self._why = 'fallback'
    return 'unknown'

  def get_why(self) -> str:
    """Returns why we chose a particular language."""
    assert self._why, 'Must call get_language first'
    return self._why

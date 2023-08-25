import platform
import subprocess

from absl import logging

_DARWIN = 'Darwin'
_LINUX = 'Linux'
_WINDOWS = 'Windows'


def open_browser(url: str):
  """Opens the browser to the login page."""
  system = platform.system()
  if system == _DARWIN:
    cmd = ['open', url]
  elif system == _LINUX:
    cmd = ['xdg-open', url]
  elif system == _WINDOWS:
    logging.info(
        'I can\'t imagine this is going to work on Windows, but feel free to '
        'give it a try and report back')
    cmd = ['cmd', '/c', 'start', url.replace('&', '^&')]
  else:
    raise RuntimeError(f'Unsupported system: {system}')
  try:
    subprocess.run(cmd, check=True, capture_output=True)
  except subprocess.CalledProcessError as e:
    if e.stdout:
      print(e.stdout)
    raise e
  # Unhandled: FileNotFoundError

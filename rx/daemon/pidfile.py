"""Manages daemon pid file."""
import os
import pathlib

from rx.client.configuration import config_base


class PidFile:
  def __init__(self, rxroot: pathlib.Path) -> None:
    self._pidfile = config_base.get_config_dir(rxroot) / 'daemon.pid'

  @property
  def filename(self) -> pathlib.Path:
    return self._pidfile

  @property
  def pid(self) -> int:
    """Read the pid from the pidfile."""
    try:
      with self._pidfile.open(mode='rt', encoding='utf-8') as pf:
        pid = int(pf.read().strip())
    except IOError:
      raise NotFoundError()
    return pid

  def write(self):
    with self._pidfile.open(mode='wt', encoding='utf-8') as fh:
      fh.write(f'{os.getpid()}\n')

  def delete(self):
    try:
      # missing_ok added in 3.8.
      self._pidfile.unlink()
    except FileNotFoundError:
      pass

  def is_running(self) -> bool:
    try:
      pid = self.pid
    except NotFoundError:
      # Pid file doesn't exist.
      return False

    try:
      os.kill(pid, 0)
    except ProcessLookupError:
      # Process isn't running.
      return False
    # PID file exists and process was found.
    return True


class NotFoundError(RuntimeError):
  """Pidfile was not found."""

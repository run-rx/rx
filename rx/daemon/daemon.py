"""Sets up the caller to be a daemon."""
import atexit
import errno
import os
import pathlib
import sys
import time
import resource
import signal
from types import TracebackType
from typing import Optional, Type

from absl import logging

from rx.daemon import pidfile


class Daemonizer:
  """Sets up daemon properties.

  This does a fork-detach-fork, closes all stdio, prevents core dumps, and
  manages the PID file."""

  def __init__(self, rxroot: pathlib.Path):
    self._rxroot = rxroot
    self._pidfile = pidfile.PidFile(rxroot)

  def __enter__(self) -> 'Daemonizer':
    self.daemonize()
    return self

  def __exit__(self, exctype: Optional[Type[BaseException]],
             excinst: Optional[BaseException],
             exctb: Optional[TracebackType]):
    if excinst:
      logging.info('Got exception: [%s] [%s] [%s]', exctype, exctb, excinst)
    self.stop()
    return False

  def daemonize(self):
    # Make sure we're in rxroot
    os.chdir(self._rxroot)
    self.prevent_core_dump()

    _fork(1)
    # Decouple from parent environment
    os.setsid()
    _fork(2)

    self.blackhole_streams()

    # Write pidfile.
    atexit.register(self._pidfile.delete)
    self._pidfile.write()

  def prevent_core_dump(self):
    """Prevents this process from generating a core dump."""
    core_resource = resource.RLIMIT_CORE

    try:
      # Ensure the resource limit exists on this platform, by requesting
      # its current value.
      resource.getrlimit(core_resource)
    except ValueError:
      # Guess we're not setting any resource limits.
      logging.exception('Failed to get resource limit')
      return

    # Set hard and soft limits to zero, i.e. no core dump at all.
    core_limit = (0, 0)
    resource.setrlimit(core_resource, core_limit)

  def blackhole_streams(self):
    """Redirect stdin, stdout, and stderr to /dev/null."""
    sys.stdout.flush()
    sys.stderr.flush()
    os.dup2(os.open(os.devnull, os.O_RDWR), sys.stdin.fileno())
    os.dup2(os.open(os.devnull, os.O_RDWR), sys.stdout.fileno())
    os.dup2(os.open(os.devnull, os.O_RDWR), sys.stderr.fileno())

  def stop(self):
    """Stop the daemon."""
    # Get the pid from the pidfile
    pid = self._pidfile.pid
    if not pid:
      sys.stderr.write(f'{self._pidfile.filename} does not exist.\n')
      return

    # Try killing the daemon process
    try:
      while True:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.1)
    except OSError as err:
      if err.errno == errno.ESRCH:
        # No such process.
        self._pidfile.delete()
      else:
        print(str(err.args))
        sys.exit(1)


def _fork(fork_no: int):
  try:
    pid = os.fork()
    if pid > 0:
      # Exit from parent.
      sys.exit(0)
  except OSError:
    logging.exception(f'Fork #{fork_no} failed')
    sys.exit(1)
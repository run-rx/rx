from collections import abc
import pathlib
import subprocess
from typing import List

from absl import flags
from absl import logging

from rx.client.configuration import config_base
from rx.client.configuration import local

_RSYNC_PATH = flags.DEFINE_string('rsync_path', None, 'Path to rsync binary')


class RsyncClient:
  """Rsync tools."""

  def __init__(
      self, sync_dir: pathlib.Path, remote_cfg: abc.Mapping):
    self._sync_dir = sync_dir
    self._cfg = remote_cfg
    self._rsync_path = _get_rsync_path()
    self._daemon_addr = self._cfg["worker_addr"]
    if config_base.is_local():
      # Remove the port (rsync isn't listening on 50051).
      self._daemon_addr = self._daemon_addr.split(':')[0]

  @property
  def host(self) -> str:
    return self._daemon_addr

  @property
  def workspace_id(self) -> str:
    return self._cfg['workspace_id']

  @property
  def _upload_path(self) -> pathlib.Path:
    return pathlib.Path(self._cfg['daemon_module'])

  def from_remote(self, source: str, dest: pathlib.Path) -> int:
    """Copies output files from the remote machine to dest."""
    assert dest.is_dir(), f'Destination {dest} must be a directory'
    remote_path = self._upload_path / source
    daemon = f'{self._daemon_addr}::{remote_path}/'
    cmd = [
        self._rsync_path,
        '--archive',
        '--compress',
        '--delete',
        '--quiet',
        f'--exclude-from={self._sync_dir / local.IGNORE}',
        daemon,
        str(dest)]
    return _run_rsync(cmd)

  def to_remote(self) -> int:
    """Copies files/dirs to remote."""
    daemon = f'{self._daemon_addr}::{self._upload_path}'
    cmd = [
        self._rsync_path,
        '--archive',
        '--compress',
        '--delete',
        '--inplace',
        f'--exclude-from={self._sync_dir / local.IGNORE}',
        f'{self._sync_dir}/',
        daemon
    ]
    return _run_rsync(cmd)


def _run_rsync(cmd: List[str]) -> int:
  logging.info('Running %s', cmd)
  try:
    result = subprocess.run(cmd, check=True, capture_output=True)
  except subprocess.CalledProcessError as e:
    logging.error('Error running `%s`', ' '.join(e.cmd))
    if e.returncode == 10:
      # Worker was unreachable.
      logging.error('stderr: %s', e.stderr)
    if e.returncode is None:
      return -1
    return e.returncode
  if result.stdout:
    print(f'stdout: {result.stdout}')
  return 0


def _get_rsync_path() -> str:
  if _RSYNC_PATH.value:
    return _RSYNC_PATH.value

  if local.is_bundled():
    return str(local.get_bundle_path() / 'bin/rsync')

  # Otherwise, use whatever's on the path.
  return 'rsync'

from collections import abc
import pathlib
import subprocess
from typing import List

from absl import logging

from rx.client.configuration import config_base
from rx.client.configuration import local


class RsyncClient:
  """Rsync tools."""

  def __init__(
      self, local_cfg: local.LocalConfig, remote_cfg: abc.Mapping):
    self._sync_dir = local_cfg.cwd
    self._cfg = remote_cfg
    self._rsync_path = local_cfg.rsync_path
    self._daemon_addr = self._cfg['worker_addr']
    if config_base.is_local(self._daemon_addr):
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
    assert dest.is_absolute(), f'Destination {dest} must be absolute'
    remote_path = self._upload_path / source
    daemon = f'{self._daemon_addr}::{remote_path}/'

    cmd = self._get_cmd_args() + [
        '--quiet',
        daemon,
        str(dest),
    ]
    return _run_rsync(cmd)

  def to_remote(self) -> int:
    """Copies files/dirs to remote."""
    daemon = f'{self._daemon_addr}::{self._upload_path}'
    # TODO: add --progress and provide info about what rsync is copying as it
    # goes. rsync's progress format looks like:
    #
    # some/path/to/file
    #     519 100%    1.12kB/s    0:00:00 (xfer#2709, to-check=2/3377)
    cmd = self._get_cmd_args() + [
        '--inplace',
        f'{self._sync_dir}/',
        daemon
    ]
    return _run_rsync(cmd)

  def _get_cmd_args(self) -> List[str]:
    """Returns the standard args for all rsync commands."""
    cmd = [
      self._rsync_path,
      '--archive',
      '--compress',
      '--delete',
    ]
    # Only add the rxignore option if the file exists.
    rxignore = self._sync_dir / local.IGNORE
    if rxignore.exists():
      cmd.append(f'--exclude-from={rxignore}')
    return cmd


def _run_rsync(cmd: List[str]) -> int:
  logging.info('Running %s', cmd)
  try:
    result = subprocess.run(cmd, check=True, capture_output=True)
  except subprocess.CalledProcessError as e:
    logging.error('Error running `%s` (%s)', ' '.join(e.cmd), e.returncode)
    if e.returncode == 10:
      # Worker was unreachable.
      logging.error('stderr: %s', e.stderr.decode('utf-8'))
    if e.returncode is None:
      return -1
    return e.returncode
  if result.stdout:
    print(f'stdout: {result.stdout.decode("utf-8")}')
  return 0

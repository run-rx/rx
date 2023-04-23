import pathlib
import sys
import unittest
from unittest import mock

from absl import flags
from absl.testing import absltest
from absl.testing import flagsaver

from rx.client import rsync

FLAGS = flags.FLAGS

class RsyncTests(unittest.TestCase):

  def setUp(self) -> None:
    super().setUp()
    FLAGS(sys.argv)
    self._cwd = pathlib.Path('/path/to/proj')
    self._remote_cfg = {
      'daemon_module': 'f1d1df3b-e046-4e88-822e-72596e5020c5',
      'worker_addr': 'abc123.trex.run-rx.com',
      'workspace_id': 'f1d1df3b-e046-4e88-822e-72596e5020c5',
    }

  @flagsaver.flagsaver(rsync_path='/path/to/rsync')
  def test_from_remote(self):
    client = rsync.RsyncClient(self._cwd, self._remote_cfg)
    rsync._run_rsync = mock.MagicMock(return_value=0)

    got = client.from_remote('rx-out', pathlib.Path('rx-out'))

    self.assertEqual(got, 0)
    rsync._run_rsync.assert_called_once_with([
      '/path/to/rsync',
      '--archive',
      '--compress',
      '--delete',
      '--exclude-from=/path/to/proj/.rxignore',
      'abc123.trex.run-rx.com::f1d1df3b-e046-4e88-822e-72596e5020c5/rx-out/',
      'rx-out',
    ])

  @flagsaver.flagsaver(rsync_path='/path/to/rsync')
  def test_to_remote(self):
    client = rsync.RsyncClient(self._cwd, self._remote_cfg)
    rsync._run_rsync = mock.MagicMock(return_value=0)

    got = client.to_remote()

    self.assertEqual(got, 0)
    rsync._run_rsync.assert_called_once_with([
      '/path/to/rsync',
      '--archive',
      '--compress',
      '--delete',
      '--inplace',
      '--exclude-from=/path/to/proj/.rxignore',
      '/path/to/proj/',
      'abc123.trex.run-rx.com::f1d1df3b-e046-4e88-822e-72596e5020c5',
    ])


if __name__ == '__main__':
  absltest.main()
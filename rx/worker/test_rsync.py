import pathlib
import sys
import unittest
from unittest import mock

from absl import flags
from absl.testing import absltest

from rx.client.configuration import local
from rx.worker import rsync

FLAGS = flags.FLAGS


class MockLocalConfig(local.LocalConfig):
  def __init__(self, config):
    self._cwd = '/path/to/proj'
    self._config = config


class RsyncTests(unittest.TestCase):

  def setUp(self) -> None:
    super().setUp()
    FLAGS(sys.argv)
    self._cwd = pathlib.Path('/path/to/proj')
    self._local_cfg = local.LocalConfig(
      cwd=self._cwd,
      remote='default',
      project_name='test',
      rsync_path='/usr/bin/rsync',
      should_sync=False)
    self._remote_cfg = {
      'daemon_module': 'f1d1df3b-e046-4e88-822e-72596e5020c5',
      'worker_addr': 'abc123.trex.run-rx.com',
      'workspace_id': 'f1d1df3b-e046-4e88-822e-72596e5020c5',
    }

  def test_from_remote(self):
    client = rsync.RsyncClient(self._local_cfg, self._remote_cfg)
    rsync._run_rsync = mock.MagicMock(return_value=0)

    outdir = pathlib.Path(absltest.TEST_TMPDIR.value)
    outdir.mkdir(parents=True, exist_ok=True)
    got = client.from_remote('rx-out', outdir)

    self.assertEqual(got, 0)
    rsync._run_rsync.assert_called_once_with([
      '/usr/bin/rsync',
      '--archive',
      '--compress',
      '--delete',
      '--quiet',
      'abc123.trex.run-rx.com::f1d1df3b-e046-4e88-822e-72596e5020c5/rx-out/',
      str(outdir),
    ])

  def test_to_remote(self):
    client = rsync.RsyncClient(self._local_cfg, self._remote_cfg)
    rsync._run_rsync = mock.MagicMock(return_value=0)

    got = client.to_remote()

    self.assertEqual(got, 0)
    rsync._run_rsync.assert_called_once_with([
      '/usr/bin/rsync',
      '--archive',
      '--compress',
      '--delete',
      '--inplace',
      '/path/to/proj/',
      'abc123.trex.run-rx.com::f1d1df3b-e046-4e88-822e-72596e5020c5',
    ])

  def test_execlude_file(self):
    # TODO: create .rxignore using tmpfile.
    pass


if __name__ == '__main__':
  absltest.main()
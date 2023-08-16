import json
import pathlib
import shutil
import tempfile
from typing import Any, Dict
import unittest

from absl.testing import absltest
from absl.testing import flagsaver

from rx.proto import rx_pb2
from rx.client.configuration import local


class LocalTests(unittest.TestCase):

  def setUp(self) -> None:
    super().setUp()
    self._rxroot = pathlib.Path(tempfile.mkdtemp())
    local._install_local_files(self._rxroot)

  def tearDown(self) -> None:
    super().tearDown()
    shutil.rmtree(self._rxroot)

  def test_create_default_local_config(self):
    cfg = local.create_local_config(self._rxroot)

    self.assertEqual(cfg['project_name'], self._rxroot.name)
    self.assertEqual(cfg['remote'], '.rx/remotes/default')

  @flagsaver.flagsaver(remote='test')
  def test_create_target_env(self):
    remote_config = {
      "image": {
        "docker": "abc123"
      },
      "hardware": {
        "processor": "xpu"
      }
    }
    self._create_remote(remote_config)
    cfg = local.create_local_config(self._rxroot)

    got = cfg.get_target_env()

    expected = rx_pb2.Environment(
      alloc=rx_pb2.Remote(
        image=rx_pb2.Remote.Image(docker='abc123'),
        hardware=rx_pb2.Hardware(processor='xpu'),
      ),
      sh='/bin/bash',
    )
    self.assertEqual(got, expected)

  @flagsaver.flagsaver(remote='no-hardware')
  def test_no_hardware(self):
    remote_config = {
      "image": {
        "docker": "python:1.2.3"
      }
    }
    self._create_remote(remote_config, 'no-hardware')
    cfg = local.create_local_config(self._rxroot)

    got = cfg.get_target_env()

    expected = rx_pb2.Environment(
      alloc=rx_pb2.Remote(
        image=rx_pb2.Remote.Image(docker='python:1.2.3'),
      ),
      sh='/bin/bash',
    )
    self.assertEqual(got, expected)

  def _create_remote(self, cfg: Dict[str, Any], remote_name: str = 'test'):
    remote_config_file = self._rxroot / remote_name
    with remote_config_file.open(mode='wt', encoding='utf-8') as fh:
      json.dump(cfg, fh)


if __name__ == '__main__':
  absltest.main()

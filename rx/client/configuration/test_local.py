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

  def tearDown(self) -> None:
    super().tearDown()

  def test_create_default_local_config(self):
    cfg = local.create_local_config(self._rxroot, False)

    self.assertEqual(cfg.project_name, self._rxroot.name)
    self.assertEqual(cfg.remote, '.rx/remotes/default')

  @flagsaver.flagsaver(remote='test')
  def test_create_target_env(self):
    remote_config = {
      "image": {
        "repository": "abc/def"
      },
      "remote": {
        "hardware": {
          "processor": "xpu"
        }
      }
    }
    self._create_remote(remote_config)
    cfg = local.create_local_config(self._rxroot, False)

    got = cfg.get_target_env()

    expected = rx_pb2.Environment(
      remote=rx_pb2.Remote(
        hardware=rx_pb2.Hardware(processor='xpu'),
      ),
      image=rx_pb2.Image(repository='abc/def'),
    )
    self.assertEqual(got, expected)

  @flagsaver.flagsaver(remote='no-hardware')
  def test_no_hardware(self):
    remote_config = {
      "image": {
        "repository": "python",
        "tag": "1.2.3"
      }
    }
    self._create_remote(remote_config, 'no-hardware')
    cfg = local.create_local_config(self._rxroot, False)

    got = cfg.get_target_env()

    expected = rx_pb2.Environment(
      image=rx_pb2.Image(repository='python', tag='1.2.3'),
    )
    self.assertEqual(got, expected)

  def test_env_conversion(self):
    env_dict = {
      'image': {
        'repository': 'python',
        'tag': '1.2.3',
        'environment_variables': {
          'DEV_AUTH': True,
          'SEED': 123,
          'STR': 'hello world',
        }
      }
    }

    got = local.env_dict_to_pb(env_dict)

    expected = rx_pb2.Environment(
      image=rx_pb2.Image(
        repository='python',
        tag='1.2.3',
        environment_variables={
          'DEV_AUTH': 'true',
          'SEED': '123',
          'STR': 'hello world',
        }),
    )
    self.assertEqual(got, expected)

  def _create_remote(self, cfg: Dict[str, Any], remote_name: str = 'test'):
    remote_config_file = self._rxroot / remote_name
    with remote_config_file.open(mode='wt', encoding='utf-8') as fh:
      json.dump(cfg, fh)


if __name__ == '__main__':
  absltest.main()

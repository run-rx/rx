import pathlib
import tempfile
import unittest

import yaml

from rx.client.configuration import local
from rx.proto import rx_pb2
from rx.trex.toolchain import toolchain


def get_local_cfg(rxroot: pathlib.Path) -> local.LocalConfig:
  return local.LocalConfig(
        cwd=rxroot,
        project_name='test',
        rsync_path='/usr/bin/rsync',
  )


class ToolchainTest(unittest.TestCase):

  def setUp(self) -> None:
    super().setUp()
    self._tmpdir = tempfile.TemporaryDirectory()
    self._rxroot = pathlib.Path(self._tmpdir.name)
    self._remote_dir = self._rxroot / local.REMOTE_DIR
    self._remote_dir.mkdir(parents=True)

  def tearDown(self) -> None:
    super().tearDown()
    self._tmpdir.cleanup()

  def test_toolchain_is_written(self):
    t = toolchain.Toolchain(get_local_cfg(self._rxroot))

    config = rx_pb2.Environment(
      image=rx_pb2.Image(repository='node', tag='slim'))
    t.save_config(config)

    with (self._remote_dir / 'default').open(mode='rt', encoding='utf-8') as fh:
      got = yaml.safe_load(fh)
    self.assertEqual(got, {'image': {'repository': 'node', 'tag': 'slim'}})

  def test_default_isnt_overwritten(self):
    default_file = self._remote_dir / 'default'
    default_config = {'image': {'repository': 'foo'}}
    with default_file.open(mode='wt', encoding='utf-8') as fh:
      yaml.dump(default_config, fh)
    t = toolchain.Toolchain(get_local_cfg(self._rxroot))

    config = rx_pb2.Environment(
      image=rx_pb2.Image(repository='bar'))
    t.save_config(config)

    with default_file.open(mode='rt', encoding='utf-8') as fh:
      got = yaml.safe_load(fh)
    self.assertEqual(got, default_config)

  def test_default_symlink_to_nowhere_is_overwritten(self):
    default_file = self._remote_dir / 'default'
    default_file.symlink_to('does_not_exist')
    t = toolchain.Toolchain(get_local_cfg(self._rxroot))

    config = rx_pb2.Environment(
      image=rx_pb2.Image(repository='node', tag='slim'))
    config_file = t.save_config(config)
    assert config_file
    got = (self._rxroot / config_file).resolve()

    # Make sure default is now symlinked to the config.
    expected = default_file.resolve()
    self.assertEqual(got, expected)

  def test_same_env_isnt_written(self):
    # Create a default remote config.
    default_file = self._remote_dir / 'default'
    with default_file.open(mode='wt', encoding='utf-8') as fh:
      yaml.dump({'image': {'repository': 'node', 'tag': 'slim'}}, fh)
    t = toolchain.Toolchain(get_local_cfg(self._rxroot))

    # "Save" a config that's the same as the one we started with.
    config = rx_pb2.Environment(
      image=rx_pb2.Image(repository='node', tag='slim'))
    t.save_config(config)

    # Make sure only the default file exists.
    files = list(self._remote_dir.glob('*'))
    self.assertListEqual(files, [default_file])

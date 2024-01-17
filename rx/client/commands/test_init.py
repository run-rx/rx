import io
import pathlib
import shutil
import sys
import unittest
from unittest import mock

from absl.testing import absltest
from absl.testing import flagsaver

from rx.client.commands import init
from rx.client.configuration import local


class InitTests(unittest.TestCase):

  def setUp(self) -> None:
    super().setUp()
    self.maxDiff = None
    shutil.rmtree(absltest.get_default_test_tmpdir())
    pathlib.Path(absltest.get_default_test_tmpdir()).mkdir()

  def test_rxroot_flag(self):
    tmpdir = absltest.get_default_test_tmpdir()
    rxroot = pathlib.Path(tmpdir) / 'foo'
    rxroot.mkdir(exist_ok=True)

    with flagsaver.flagsaver(rxroot=str(rxroot)):
      got = init.InitCommand([])

    self.assertEqual(got.rxroot, rxroot)

  def test_no_rxroot(self):
    got = init.InitCommand([])

    self.assertEqual(got.rxroot, pathlib.Path.cwd())

  def test_existing_rxroot_message(self):
    tmpdir = absltest.get_default_test_tmpdir()
    rxroot = pathlib.Path(tmpdir) / 'foo'
    rxroot.mkdir(exist_ok=True)
    local.create_local_config(rxroot)

    with flagsaver.flagsaver(rxroot=str(rxroot)), \
        mock.patch.object(sys, 'stdout', new=io.StringIO()) as mock_stdout, \
        mock.patch.object(sys, 'stdin', io.StringIO('y\ny')):
      cmd = init.InitCommand([])
      cmd._show_init_message()

    got = mock_stdout.getvalue()

    self.assertIn(
      'Looks like you already have an rx workspace.', got)
    self.assertIn(
      '1. Shut down your existing virtual machine.', got)

  def test_new_rxroot_message(self):
    tmpdir = absltest.get_default_test_tmpdir()
    rxroot = pathlib.Path(tmpdir) / 'foo'
    rxroot.mkdir(exist_ok=True)

    with flagsaver.flagsaver(rxroot=str(rxroot)), \
        mock.patch.object(sys, 'stdout', new=io.StringIO()) as mock_stdout, \
        mock.patch.object(sys, 'stdin', io.StringIO('y')):
      cmd = init.InitCommand([])
      cmd._show_init_message()

    got = mock_stdout.getvalue()

    self.assertIn('To set up rx, this command will:', got)
    self.assertIn('3. Copy the files', got)


if __name__ == '__main__':
  absltest.main()

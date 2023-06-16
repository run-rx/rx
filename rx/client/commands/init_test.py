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
      got = init.InitCommand()

    self.assertEqual(got.rxroot, rxroot)

  def test_no_rxroot(self):
    got = init.InitCommand()

    self.assertEqual(got.rxroot, pathlib.Path.cwd())

  def test_existing_rxroot_message(self):
    tmpdir = absltest.get_default_test_tmpdir()
    rxroot = pathlib.Path(tmpdir) / 'foo'
    rxroot.mkdir(exist_ok=True)
    local.create_local_config(rxroot)

    with flagsaver.flagsaver(rxroot=str(rxroot)), \
        mock.patch.object(sys, 'stdout', new=io.StringIO()) as mock_stdout, \
        mock.patch.object(sys, 'stdin', io.StringIO('y\ny')):
      cmd = init.InitCommand()
      cmd._show_init_message()

    expected = f"""Looks like you already have an rx workspace. Would you like to stop that one
and start a new one? (Y/n): Got it. To re-init this workspace, rx will:

1. Shut down your existing virtual machine.
2. Create an account for you with rx (or log you into your existing account).
3. Set up a virtual machine on the cloud (on AWS).
4. Copy over the files in this directory ({rxroot}) to your
   virtual machine.

Would you like to proceed with logging in/creating an rx account? (Y/n): """
    self.assertEqual(expected, mock_stdout.getvalue())

  def test_new_rxroot_message(self):
    tmpdir = absltest.get_default_test_tmpdir()
    rxroot = pathlib.Path(tmpdir) / 'foo'
    rxroot.mkdir(exist_ok=True)

    with flagsaver.flagsaver(rxroot=str(rxroot)), \
        mock.patch.object(sys, 'stdout', new=io.StringIO()) as mock_stdout, \
        mock.patch.object(sys, 'stdin', io.StringIO('y')):
      cmd = init.InitCommand()
      cmd._show_init_message()

    expected = f"""To set up rx, this command will:

1. Create an account for you with rx (or log you into your existing account).
2. Set up a virtual machine on the cloud (on AWS).
3. Copy over the files in this directory ({rxroot}) to your
   virtual machine.

Would you like to proceed with logging in/creating an rx account? (Y/n): """
    self.assertEqual(expected, mock_stdout.getvalue())


if __name__ == '__main__':
  absltest.main()

import argparse
import unittest

from rx.client.commands import command
from rx.client.commands import exec
from rx.client.commands import init
from rx.client.commands import runner


class ExecTests(unittest.TestCase):

  def test_flag_parsing_cmd(self):
    got = exec.parse_flags_with_usage(['rx', 'init', '--dry-run'])

    want = command.CommandLine(
      ns=argparse.Namespace(func=init._run_cmd),
      remainder=[],
      original=['rx', 'init', '--dry-run']
    )
    self.assertEqual(got, want)

  def test_flag_parsing_implied_run(self):
    got = exec.parse_flags_with_usage(['rx', 'ls', '-l'])

    want = command.CommandLine(
      ns=argparse.Namespace(func=runner._run_cmd),
      remainder=['ls', '-l'],
      original=['rx', 'ls', '-l']
    )
    self.assertEqual(got, want)

  def test_required_arg_found(self):
    got = exec.get_first_required_arg(['--remote=r', 'init', '--dry-run'])
    self.assertEqual(got, 'init')

    got = exec.get_first_required_arg(['--dry-run', '-remote=x'])
    self.assertIsNone(got)

"""Checks that packaging worked correctly."""
import os
from packaging import version
import re
import tarfile
from typing import Tuple
import unittest

from absl import flags
import toml

from rx.client.configuration import local

FLAGS = flags.FLAGS

IGNORE = [
  '__pycache__',
  '^.git',
  '^.pylintrc',
  '^.pytest_cache',
  '^.rx',
  '^.rxignore',
  '^.venv',
  '^.vscode',
  '^build',
  '^dist',
  '^integration_test.sh$',
  '^release.sh',
  '^requirements.txt',
  '^requirements_dev.txt',
  '^run_tests.py$',
  '^rx-out',
  '\\btest_.*.py$',
  '\\b__init__.py$',
  '.proto$',
]

REMOVE_REQS = [
  'certifi',
  'charset-normalizer',
  'idna',
  'urllib3',
]


class PackagingTests(unittest.TestCase):
  def test_tgz_contains_all_dirs(self):
    tgz_version, tgz_path = _get_latest_tgz()
    tarf = tarfile.open(tgz_path, 'r:gz')
    tar_ent = tarf.getnames()
    for path, _, files in os.walk('.'):
      for name in files:
        target = os.path.normpath(os.path.join(path, name))
        if os.path.isdir(target):
          # tar file doesn't contain plain dirs.
          continue
        if _ignorable(target):
          continue
        # Everything in the package is prefixed with 'run_rx-version/'
        pkg_path = os.path.join(f'run_rx-{tgz_version}', target)
        self.assertIn(
          pkg_path, tar_ent, f'Missing file {pkg_path} in {tgz_path}')


class TomlTests(unittest.TestCase):

  def setUp(self) -> None:
    super().setUp()
    with open('pyproject.toml', mode='rt', encoding='utf-8') as fh:
      self._pyproject = toml.load(fh)

  def test_version_matches_in_code_and_config(self):
    self.assertEqual(
      local.VERSION, self._pyproject['tool']['poetry']['version'])

  def test_requirements_all_there(self):
    got = list(self._pyproject['tool']['poetry']['dependencies'].keys())
    got.remove('python')

    reqs = open('requirements.txt', 'r')
    expected = [x.split('==')[0] for x in reqs.readlines()]
    for rr in REMOVE_REQS:
      expected.remove(rr)
    self.assertEqual(got, expected)


def _get_latest_tgz() -> Tuple[version.Version, str]:
  dist = os.listdir('dist')
  max_version = version.parse('0.0.1')
  max_tgz = None
  # Format of each file: run_rx-x.y.z.tar.gz
  for f in dist:
    if not f.endswith('tar.gz'):
      # Wheel file.
      continue
    v = version.parse(f[7:-7])
    if v > max_version:
      max_version = v
      max_tgz = f
  assert max_tgz is not None, 'No .tar.gzs in dist/'
  return max_version, os.path.join('dist', max_tgz)


def _ignorable(target: str):
  for x in IGNORE:
    if re.search(x, target) is not None:
      return True
  return False

import unittest

from rx.trex.toolchain import lang_detector
from rx.trex.toolchain import manifest

D = lang_detector.DetectedTool


class LanguageTest(unittest.TestCase):

  def test_lang_from_package_manager(self):
    m = manifest.Manifest(['requirements.txt', 'environment.yml'])
    d = lang_detector.Detector(m)

    got = d.get_languages()

    self.assertEqual(len(got), 2, str(got))
    want = set([
      D(name='conda', why='package manager'),
      D(name='pip', why='package manager'),
    ])
    self.assertSetEqual(set(got), want)

  def test_lang_from_manifest(self):
    m = manifest.Manifest([
      'src/hello.cc', 'src/hello.h', 'src/bye.cc', 'config.in'])
    d = lang_detector.Detector(m)

    got = d.get_languages()

    self.assertListEqual(got, [D(name='cpp', why='file extension')])

  def test_unknown_lang(self):
    m = manifest.Manifest(['x.foo', 'y.foo', 'z.bar'])
    d = lang_detector.Detector(m)

    got = d.get_languages()

    self.assertListEqual(got, [])

  def test_multiple_matches(self):
    m = manifest.Manifest(['package.json', 'foo.js', 'bar.tsx'])
    d = lang_detector.Detector(m)

    got = d.get_languages()

    self.assertListEqual(got, [D(name='node', why='package manager')])

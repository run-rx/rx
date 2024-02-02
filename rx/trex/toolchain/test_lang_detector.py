import unittest

from rx.trex.toolchain import lang_detector
from rx.trex.toolchain import manifest


class LanguageTest(unittest.TestCase):

  def test_lang_from_pm(self):
    m = manifest.Manifest(['requirements.txt', 'environment.yml'])
    d = lang_detector.Detector(m)

    got = d.get_language()

    self.assertEqual(got, 'conda')

  def test_lang_from_manifest(self):
    m = manifest.Manifest([
      'src/hello.cc', 'src/hello.h', 'src/bye.cc', 'config.in'])
    d = lang_detector.Detector(m)

    got = d.get_language()

    self.assertEqual(got, 'cpp')

  def test_unknown_lang(self):
    m = manifest.Manifest(['x.foo', 'y.foo', 'z.bar'])
    d = lang_detector.Detector(m)

    got = d.get_language()

    self.assertEqual(got, 'unknown')

import unittest

from rx.trex.toolchain import manifest


class ManifestTest(unittest.TestCase):

  def test_languages_returned_by_popularity(self):
    files = (
      ['baz.rs'] + ['foo.go'] * 3 + ['bar.java'] * 4 + ['baz.rs'] + ['.bashrc'])
    m = manifest.Manifest(files)

    got = list(m.most_popular_extensions())

    self.assertListEqual(got, ['.java', '.go', '.rs', ''])

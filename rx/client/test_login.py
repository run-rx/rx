import math
import time
import unittest

from rx.client import login

class LoginTests(unittest.TestCase):

  def test_expired_ts(self):
    past = math.floor(time.time()) - 10
    self.assertTrue(login.is_expired({'exp': past}))

  def test_not_expired(self):
    future = math.floor(time.time()) + 1000
    self.assertFalse(login.is_expired({'exp': future}))


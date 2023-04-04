import unittest

from rx.client import user


class UserTests(unittest.TestCase):

  def test_username_too_short(self):
    self.assertFalse(user.username_validator(None))
    self.assertFalse(user.username_validator(''))
    self.assertFalse(user.username_validator('x'))

  def test_username_too_long(self):
    self.assertFalse(user.username_validator('a012345678901234'))

  def test_username_invalid(self):
    self.assertFalse(user.username_validator('123abc'))
    self.assertFalse(user.username_validator('x.y.com'))

  def test_valid_username(self):
    # Min length.
    self.assertTrue(user.username_validator('abc'))
    self.assertTrue(user.username_validator('abc123'))
    self.assertTrue(user.username_validator('abc_123'))
    # Max length.
    self.assertTrue(user.username_validator('a01234567890123'))

"""Handles client-side user functionality.

The user info is stored in .rx/user/config and includes the user's username.
"""
import pathlib
import re
from typing import Optional

from rx.client import menu
from rx.client.configuration import config_base

_VALID_USERNAME = re.compile(r'^[a-zA-Z][\w]{2,14}$')


class CreateUser(config_base.ReadWriteConfig):
  def __init__(self, cwd: pathlib.Path):
    super().__init__(_get_user_config(cwd))


class User(config_base.ReadOnlyConfig):
  """User info."""
  def __init__(
      self,
      cwd: pathlib.Path,
      email: Optional[str] = None,
      strict: bool = True):
    super().__init__(_get_user_config(cwd))
    if strict and email != self._config['email']:
      raise RuntimeError(f'Mismatched emails: {email} vs. {self["email"]}')


def has_config(cwd: pathlib.Path) -> bool:
  return _get_user_config(cwd).exists()


def username_prompt(email: str) -> str:
  """Prompts the user to choose a username."""
  return menu.string_prompt(
      f'Choose a username for {email}', validation=username_validator)


def username_validator(username: Optional[str]) -> bool:
  """Returns if username is valid."""
  is_valid = (
    username is not None and _VALID_USERNAME.match(username) is not None)
  if not is_valid:
    if username is None or len(username) < 3:
      print('Error: username too short.')
    elif username is not None and len(username) > 15:
      print('Error: username too long.')
    else:
      print('Error: username must contain only alphanumeric characters.')
  return is_valid


def _get_user_config(rxroot: pathlib.Path) -> pathlib.Path:
  return rxroot / config_base.get_config_dir(rxroot) / 'user/config.yaml'

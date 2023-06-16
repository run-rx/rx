"""Text menus.

Each helper function has the same general structure:

1. Setup the prompt.
2. Convert the response to the expected type.
2. Validate the response. If validation fails, go back to 1.
"""

import pathlib
from typing import Any, Callable, List, Optional

from absl import flags

_QUIET = flags.DEFINE_bool(
    'quiet', False, 'Don\'t prompt for user confirmation, go with the default '
    'option automatically')


def bool_prompt(prompt: str, default_opt: str = '') -> bool:
  assert default_opt in ['', 'y', 'n']
  if _QUIET.value and default_opt:
    return default_opt == 'y'
  y = 'Y' if default_opt == 'y' else 'y'
  n = 'N' if default_opt == 'n' else 'n'
  response = input(f'{prompt} ({y}/{n}): ')
  if not response:
    response = default_opt
  response = response.lower()
  if response == 'y':
    return True
  elif response == 'n':
    return False
  print('Please choose "y" or "n".')
  return bool_prompt(prompt)


def numbered_options_prompt(
    prompt: str, options: List[Any], default: int = 0) -> int:
  """Prompt with a numbered list of options."""
  if _QUIET.value:
    return default

  # Setup
  assert options
  print(prompt)
  for i, p in options:
    print(f'{i}: {p}')
  response = input(f'[{default}]: ')

  # Convert.
  if not response:
    return 0
  response = int(response)

  # Validation.
  if response >= len(options):
    print(f'Must be between 0 and {len(options) - 1}')
    return numbered_options_prompt(prompt, options, default)
  return response


def path_prompt(
  prompt: str,
  default_path: Optional[pathlib.Path],
  validation: Callable[[Optional[pathlib.Path]], bool] = lambda x: True
) -> pathlib.Path:
  """Prompt for filesystem path."""
  if _QUIET.value and default_path:
    return default_path

  # Setup.
  if default_path:
    response = input(f'{prompt}\n[{default_path}]: ')
  else:
    response = input(f'{prompt}: ')

  # Convert.
  if not response and default_path:
    response = default_path
  else:
    response = pathlib.Path(response)

  # Validation.
  if not validation(response):
    return path_prompt(prompt, default_path, validation)
  return response


def string_prompt(
  prompt: str,
  default_str: Optional[str] = None,
  validation:  Callable[[Optional[str]], bool] = lambda x: True
) -> str:
  if _QUIET.value and default_str:
    return default_str

  # Setup.
  if default_str:
    response = input(f'{prompt}\n[{default_str}]: ')
  else:
    response = input(f'{prompt}: ')

  # Convert.
  if not response and default_str:
    response = default_str

  # Validation.
  if not validation(response):
    return string_prompt(prompt, default_str, validation)
  return response

import pathlib

from rx.client import browser
from rx.client import menu
from rx.client import user
from rx.client.configuration import config_base

# Default URL for local website (npm run dev)
_LOCAL_ADDR = 'http://localhost:3000'


def request_subscription(cwd: pathlib.Path, force: bool = True) -> bool:
  """Returns if the user subscribed."""
  if not user.has_config(cwd):
    raise RuntimeError('No user info found, try running rx init first.')
  u = user.User(cwd, strict=False)

  reason_for_subscription = ''
  if force:
    reason_for_subscription = '\nYour free compute has been exhausted!\n'
  pay = menu.bool_prompt(f"""{reason_for_subscription}
Would you like to create a subscription to continue to use rx?

(This will open a browser window to collect payment infomation.)""", 'y')

  if not pay:
    print("""
Sorry to hear that! Please email us at at eng@run-rx.com know if you have any
feedback or suggestions.""")
    return False

  host = _LOCAL_ADDR if _is_local() else 'https://run-rx.com'
  url = f'{host}/pricing?user={u["username"]}'
  print(f'Opening your browser. Or, you can manually visit:\n\n\t{url}\n')
  browser.open_browser(url)

  print("""
Thank you! Your subscription will be activated as soon as your payment is
processed (that may take a few minutes).""")

  # TODO: wait for payment to succeed.
  return True


def _is_local():
  return config_base.TREX_HOST.value.startswith('localhost')

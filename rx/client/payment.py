import pathlib

from rx.client import browser
from rx.client import menu
from rx.client import user

def request_subscription(cwd: pathlib.Path) -> bool:
  """Returns if the user subscribed."""
  if not user.has_config(cwd):
    raise RuntimeError('No user info found, try running rx init.')
  u = user.User(cwd, strict=False)

  pay = menu.bool_prompt(
            f"""
Your free compute has been exhausted!

Would you like to create a subscription to continue to use rx?

(This will open a browser window to collect payment infomation.)""", 'y')

  if not pay:
    print("""
Sorry to hear that! Please let us know if you have any feedback or suggestions
at eng@run-rx.com. Thanks for trying it out!""")
    return False

  browser.open_browser(f'https://run-rx.com/pricing?user={u["username"]}')

  print("""
Thank you! It may take a few minutes for your payment to be processed, but then
your subscription will be activated.""")
  return True

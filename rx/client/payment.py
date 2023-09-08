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

  url = f'https://run-rx.com/pricing?user={u["username"]}'
  print(f'Opening your browser. Or, you can manually visit:\n\n\t{url}\n')
  browser.open_browser(url)

  print("""
Thank you! Your subscription will be activated as soon as your payment is
processed (that may take a few minutes).""")
  return True

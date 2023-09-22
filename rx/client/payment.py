import pathlib

from rx.client import browser
from rx.client import menu
from rx.client import user
from rx.proto import rx_pb2


_GPU = """
Subscriptions are charged via a monthly flat fee, plus an hourly charge if you
use a GPU:

    * $19.99/month for init-ing machines and storing your workspace.
    * $3/hour for using an H100 GPU.

GPU usage is only charged for hours when you have `rx run` commands on a GPU
workspace. rx will automatically stop charging you if you aren't using a GPU.
You can run `rx workspace-info` to check if your workspace is using a GPU.

Loading and saving your environment (`rx init` and `rx stop`) are covered by the
monthly fee, even on GPU machines, meaning you never have to worry about setting
up your environemnt on a new machine again.

Finally, canceling your subscription is hassle-free: run `rx unsubscribe` at any
time.

See https://run-rx.com/pricing for more info.
"""


def explain_subscription(cwd: pathlib.Path) -> bool:
  """Returns if the user subscribed."""
  if not user.has_config(cwd):
    raise RuntimeError('No user info found, try running rx init first.')

  pay = menu.bool_prompt(f"""

Create a subscription
=====================
{_GPU}
Would you like to continue? (This will open a browser window to collect payment
infomation.)""", 'y')

  if not pay:
    print("""
Sorry to hear that! Please email us at at eng@run-rx.com know if you have any
feedback or suggestions.""")
    return False
  return True


def open_browser(sub: rx_pb2.SubscribeInfo):
  url = sub.payment_link
  if not url:
    print(
      f'No url found for {sub}, visit https://run-rx.com/pricing to sign up.')
    return
  print(f'Opening your browser. Or, you can manually visit:\n\n{url}\n')
  browser.open_browser(url)

  print("""
Thank you! Your subscription will be activated as soon as your payment is
processed (that may take a few minutes).""")


def success():
  print("""

Subscription activated! Thank you for choosing rx.
""")

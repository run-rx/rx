import pathlib

from rx.client import browser
from rx.client import menu
from rx.client import user
from rx.proto import rx_pb2

_CPU = """
Your free compute has been exhausted! Subscribe for $9.99/month to continue
using unlimited CPU compute. This plan comes with 64GB of storage and can be
canceled anytime by running `rx stop --unsubscribe`.
"""

_GPU = """
Your free GPU compute has been exhausted! Subscribe to continue using
compute and storage:

    * $19.99/month, which covers init-ing GPU machines and storing your
      workspace.
    * $3/hour for using compute.

rx helps you save on compute in several ways. First, much of the setup you have
to do for a GPU is done: no futzing with driver configs in vi while the clock
ticks. You may still do some custom project setup, but rx will automatically
save that state so you only have to do it once. And finally, the hourly rate is
only charged for hours when you `rx run`. You don't have to remember to shut
down your VM when you stop working for the day and it'll be ready to go the next
morning.

Finally, canceling your subscription is hassle-free: run `rx stop --unsubscribe`
at any time.
"""


def request_subscription(cwd: pathlib.Path, sub: rx_pb2.SubscribeInfo) -> bool:
  """Returns if the user subscribed."""
  if not user.has_config(cwd):
    raise RuntimeError('No user info found, try running rx init first.')

  pay = menu.bool_prompt(f"""

Create a subscription
=====================
{_GPU if sub.needs_metered else _CPU}
Would you like to subscribe? (This will open a browser window to collect payment
infomation.)""", 'y')

  if not pay:
    print("""
Sorry to hear that! Please email us at at eng@run-rx.com know if you have any
feedback or suggestions.""")
    return False

  url = sub.payment_link
  if not url:
    print(f'No url found for {sub}, visit https://run-rx.com/pricing to sign up.')
    return True
  print(f'Opening your browser. Or, you can manually visit:\n\n\t{url}\n')
  browser.open_browser(url)

  print("""
Thank you! Your subscription will be activated as soon as your payment is
processed (that may take a few minutes).""")

  # TODO: wait for payment to succeed.
  return True

import pathlib

from rx.client import browser
from rx.client import menu
from rx.client import user
from rx.proto import rx_pb2


def request_subscription(
    cwd: pathlib.Path, sub: rx_pb2.SubscribeInfo, force: bool = True) -> bool:
  """Returns if the user subscribed."""
  if not user.has_config(cwd):
    raise RuntimeError('No user info found, try running rx init first.')

  reason_for_subscription = ''
  if force:
    reason_for_subscription = '\nYour free compute has been exhausted!\n'

  if sub.needs_metered:
    message = (
      '$19.99/month for H100 access, plus $2/hour for usage. Usage is only '
      'charged for hours when you are using the GPU.')
  else:
    message = (
      '$9.99/month for unlimited access to CPU + up to 64GB of storage.')
  pay = menu.bool_prompt(
f"""{reason_for_subscription}
You will need to subscribe to continue using rx.

  * {message} See https://run-rx.com/pricing for more info.

Cancel anytime by running `rx stop --unsubscribe`.

Would you like to subscribe? (This will open a browser window to collect payment
infomation.)""", 'y')

  if not pay:
    print("""
Sorry to hear that! Please email us at at eng@run-rx.com know if you have any
feedback or suggestions.""")
    return False

  url = sub.payment_link
  print(f'Opening your browser. Or, you can manually visit:\n\n\t{url}\n')
  browser.open_browser(url)

  print("""
Thank you! Your subscription will be activated as soon as your payment is
processed (that may take a few minutes).""")

  # TODO: wait for payment to succeed.
  return True

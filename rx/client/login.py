"""Implements client login flow.

See https://developers.google.com/identity/protocols/oauth2/native-app for
details about this flow.

There are two important files:

* .rx/<addr>/user/.refresh-token
* .rx/<addr>/user/access-token

These start out the same. Access tokens expire in 1 hour, so after that, the
'refresh_token' from .refresh-token.json must be used to get a new access token.
However, the response to that request does not contain the refresh token itself,
so it is stored in .rx/user/access-token.json, which should be used for access.

Thus, .refresh-token is something of an implementation detail and access-token
is more "user-facing."
"""
import functools
import http.cookies
import http.server
import json
import pathlib
import platform
import subprocess
import threading
import time
from typing import Any, Dict, Tuple
from urllib import parse

from absl import flags
from absl import logging
import jwt
import requests
from requests import exceptions

from rx.client.configuration import config_base

_DO_AUTH = flags.DEFINE_bool(
  'do_auth', True, 'Skip auth for offline development')
_AUTH_EMAIL = flags.DEFINE_string(
  'auth_email', None, 'Email to use for offline development')

_DARWIN = 'Darwin'
_LINUX = 'Linux'
_WINDOWS = 'Windows'

# From https://console.developers.google.com/apis/credentials
_CLIENT_ID = '909912915303-enmim0gms3hfsdv7c9m6p79vovjkf4vd.apps.googleusercontent.com'
_CLIENT_SECRET = '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'


class Handler(http.server.SimpleHTTPRequestHandler):
  """Handle the response from accounts.google.com."""

  def __init__(self, holder: 'CodeHolder', *args, **kwargs):
    self._holder = holder
    super().__init__(*args, **kwargs)

  def do_GET(self):
    parsed_url = parse.urlparse(self.path)
    code = parse.parse_qs(parsed_url.query)['code'][0]
    self._holder.set_code(code)
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b'All set, feel free to close this tab')


class CodeHolder:
  def __init__(self) -> None:
    self._code_is_set = threading.Event()
    self._code = None

  @property
  def code(self) -> str:
    assert self._code
    return self._code

  def set_code(self, code: str):
    self._code = code
    self._code_is_set.set()

  def wait(self):
    self._code_is_set.wait()


class LoginManager:
  """Handle browser login."""

  def __init__(self, rxroot: pathlib.Path) -> None:
    self._rxroot = rxroot
    self._server = None
    self._port = 0
    self._code_holder = CodeHolder()
    self._access_token = config_base.ReadOnlyConfig(
      _get_access_token_file(rxroot), strict_mode=False)
    if not _DO_AUTH.value:
      self.login = _no_auth_login

  @property
  def grpc_metadata(self) -> Tuple[Tuple[str, str]]:
    """Returns the signed ID token."""
    return (('id-token', self._access_token['id_token']),)

  @property
  def id_token(self) -> Dict[str, str]:
    """Returns the decoded ID token."""
    return decode_id_token(self._access_token['id_token'])

  def login(self) -> config_base.ReadOnlyConfig:
    """Logs in and returns the access token dict.

    Dict is of the form:

    {
      "access_token": "abc...123",
      "expires_in": 3599,
      "scope": "openid https://www.googleapis.com/auth/userinfo.email",
      "token_type": "Bearer",
      "id_token": "<base64-encoded 3-part string>",
    }
    """
    user_dir = config_base.get_config_dir(self._rxroot) / 'user'
    if not user_dir.exists():
      user_dir.mkdir(parents=True, exist_ok=True)
    if not self._access_token:
      self.start_server()
      self.open_browser()
      self.wait_for_login()
    self.validate_login()
    return self._access_token

  def open_browser(self):
    """Opens the browser to the login page."""
    while self._server is None:
      time.sleep(1)
    url = self._create_login_url()
    system = platform.system()
    if system == _DARWIN:
      cmd = ['open', url]
    elif system == _LINUX:
      cmd = ['xdg-open', url]
    elif system == _WINDOWS:
      logging.info(
          'I can\'t imagine this is going to work on Windows, but feel free to '
          'give it a try and report back')
      cmd = ['cmd', '/c', 'start', url.replace('&', '^&')]
    else:
      raise RuntimeError(f'Unsupported system: {system}')
    try:
      subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
      if e.stdout:
        print(e.stdout)
      self._server.shutdown()
      raise AuthError(f'Error opening browser: {e}')
    except FileNotFoundError as e:
      self._server.shutdown()
      raise AuthError(
        f'Could not find browser-opening program {cmd[0]}, are you in an SSH '
        'session?')

  def refresh_access_token(self):
    """Refreshes the access token when it expires."""
    refresh_file = _get_refresh_token_file(self._rxroot)
    if not refresh_file.exists():
      # Access token was expired but the refresh token doesn't exist. Just start
      # over.
      _delete_auth_files(self._rxroot)
      raise AuthError('Could not log in, please try again.')
    with open(refresh_file, mode='rt', encoding='utf-8') as fh:
      refresh_token = json.load(fh)
    data = {
      'client_id': _CLIENT_ID,
      'client_secret': _CLIENT_SECRET,
      'grant_type': 'refresh_token',
      'refresh_token': refresh_token['refresh_token']
    }
    try:
      resp = requests.post(
        'https://oauth2.googleapis.com/token', data=data, timeout=10)
    except exceptions.ConnectionError:
      raise AuthError(
        f'Unable to connect to oauth2.googleapis.com, is your internet up?')
    if resp.status_code != 200:
      # Refreshing went wrong, remove everything!
      _delete_auth_files(self._rxroot)
      raise AuthError(
        f'Unable to refresh log in: {resp.reason} [{resp.status_code}]\n' +
        resp.text)
    access_token = _get_access_token_file(self._rxroot)
    with access_token.open(mode='wt', encoding='utf-8') as fh:
      fh.write(resp.text)
    self._access_token = json.loads(resp.text)

  def start_server(self):
    """Starts a local server in a separate thread."""
    th = threading.Thread(target=self._start_local_server)
    th.start()

  def validate_login(self):
    assert self._access_token
    try:
      id_token = decode_id_token(self._access_token['id_token'])
    except ValueError as e:
      _delete_auth_files(self._rxroot)
      logging.exception(e)
      raise AuthError('Could not read token, please try logging in again.')
    if is_expired(id_token):
      self.refresh_access_token()

  def wait_for_login(self):
    """Shuts down the server after login."""
    self._code_holder.wait()
    assert self._server
    self._server.shutdown()
    self._get_access_token(self._code_holder.code)

  def _create_login_url(self) -> str:
    """Generate the login URL."""
    return (
      'https://accounts.google.com/o/oauth2/v2/auth?'
      'response_type=code&'
      f'client_id={_CLIENT_ID}&'
      'scope=openid%20email&'
      f'redirect_uri=http%3A//localhost:{self._port}')

  def _get_access_token(self, code: str):
    """Exchange the identity code for an access token."""
    data = {
      'client_id': _CLIENT_ID,
      'client_secret': _CLIENT_SECRET,
      'code': code,
      'grant_type': 'authorization_code',
      # We need to provide the matching redirect URI (even though the server
      # isn't even running anymore) or Google will return a 400 error.
      'redirect_uri': f'http://localhost:{self._port}'
    }
    resp = requests.post(
      'https://oauth2.googleapis.com/token', data=data, timeout=10)
    if resp.status_code != 200:
      raise AuthError(
        f'Unable to log in: {resp.reason} [{resp.status_code}]\n{resp.text}')
    access_token = _get_access_token_file(self._rxroot)
    with access_token.open(mode='wt', encoding='utf-8') as fh:
      fh.write(resp.text)
    refresh = _get_refresh_token_file(self._rxroot)
    with refresh.open(mode='wt', encoding='utf-8') as fh:
      fh.write(resp.text)
    self._access_token = json.loads(resp.text)

  def _start_local_server(self):
    """Starts the server."""
    partial_handler = functools.partial(Handler, self._code_holder)
    self._server = http.server.HTTPServer(('localhost', 0), partial_handler)
    self._port = self._server.server_port
    self._server.serve_forever()


def _delete_auth_files(rxroot: pathlib.Path):
  """Remove all files associated with logging in."""
  if _get_refresh_token_file(rxroot).exists():
    _get_refresh_token_file(rxroot).unlink()
  if _get_access_token_file(rxroot).exists():
    _get_access_token_file(rxroot).unlink()


def is_expired(id_token: Dict[str, Any]) -> bool:
  """Returns if the access token is expired."""
  exp = id_token['exp']
  now = time.time()
  return now > exp


def decode_id_token(b64: str) -> Dict[str, Any]:
  """The id_token field is a base64 encoded, .-delimited string."""
  return jwt.decode(b64, options={'verify_signature': False})


def needs_login(rxroot: pathlib.Path) -> bool:
  return not (
    _get_access_token_file(rxroot).exists() and
    _get_refresh_token_file(rxroot).exists())


def _get_access_token_file(rxroot: pathlib.Path) -> pathlib.Path:
  return config_base.get_config_dir(rxroot) / 'user/access-token'


def _get_refresh_token_file(rxroot: pathlib.Path) -> pathlib.Path:
  return config_base.get_config_dir(rxroot) / 'user/.refresh-token'


def _no_auth_login() -> Dict[str, Any]:
  """Returns an auth token with email: foo@example.com."""
  assert not _DO_AUTH.value and _AUTH_EMAIL.value is not None
  id_token = jwt.encode({'email': _AUTH_EMAIL.value}, 'abc123')
  return {
    'access_token': 'abc123',
    'expires_in': 3599,
    'scope': 'openid https://www.googleapis.com/auth/userinfo.email',
    'token_type': 'Bearer',
    'id_token': id_token,
  }


class AuthError(RuntimeError):
  pass

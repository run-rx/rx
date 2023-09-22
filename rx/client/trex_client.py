import datetime
import sys
import time
from typing import cast, Generator, Iterable, Optional, Tuple

from absl import logging
from google.protobuf import empty_pb2
import grpc

from rx.client import grpc_helper
from rx.client import login
from rx.client import payment
from rx.client import user
from rx.client import worker_client
from rx.client.configuration import local
from rx.client.configuration import remote
from rx.client.worker import progress_bar
from rx.client.worker import rsync
from rx.proto import rx_pb2
from rx.proto import rx_pb2_grpc

_PAYMENT_TIMEOUT = datetime.timedelta(300)
_RPC_TIMEOUT_SECS = seconds=10
_SLEEP_SECS = 5

class Client:
  """Handle contacting the remote server."""

  def __init__(
      self,
      channel: grpc.Channel,
      local_cfg: local.LocalConfig,
      auth_metadata: Optional[Tuple[Tuple[str, str]]]):
    self._stub = rx_pb2_grpc.SetupServiceStub(channel)
    self._local_cfg = local_cfg
    self._metadata = local.get_grpc_metadata()
    if auth_metadata:
      self._metadata += auth_metadata

  def create_user_or_log_in(self) -> user.User:
    """This logs in the user, then checks if trex has a username for them."""

    # First, make sure we're logged in with Google.
    lm = login.LoginManager(self._local_cfg.cwd)
    try:
      lm.login()
    except login.AuthError as e:
      raise TrexError(e, -1)
    self._metadata += lm.grpc_metadata
    email = lm.id_token['email']

    # Check if user is set up.
    # TODO: it would be better to read the username from the config and
    # automatically try to set it on the remote. However, this generally
    # shouldn't come up for normal users.
    username = self._get_username(email)
    if not user.has_config(self._local_cfg.cwd):
      with user.CreateUser(self._local_cfg.cwd) as c:
        c['username'] = username
        c['email'] = email
    return user.User(self._local_cfg.cwd, email)

  def dry_run(self):
    rsync.dry_run(self._local_cfg)

  def init(self, force_subscribe: bool = False) -> int:
    try:
      target_env = self._local_cfg.get_target_env()
    except local.ConfigError as e:
      raise TrexError(str(e), -1)
    req = rx_pb2.InitRequest(
      project_name=self._local_cfg['project_name'],
      rsync_source=self._local_cfg.rsync_source,
      target_env=target_env,
      force_subscribe=force_subscribe,
    )
    # TODO: create a threaded UserStatus class with __enter__/__exit__.
    sys.stdout.write('Finding a remote worker... ')
    sys.stdout.flush()
    try:
      # Five minute timeout.
      resp = self._stub.Init(req, metadata=self._metadata, timeout=(5 * 60))
    except grpc.RpcError as e:
      e = cast(grpc.Call, e)
      raise TrexError(f'Could not initialize worker: {e.details()}', -1)
    if resp.result.code != 0:
      if resp.result.code == rx_pb2.SUBSCRIPTION_REQUIRED:
        if self.subscribe():
          # Retry init.
          raise grpc_helper.RetryError()
      else:
        raise TrexError(resp.result.message, -1)
    sys.stdout.write('Done.\n')

    with remote.WritableRemote(self._local_cfg.cwd) as r:
      r['workspace_id'] = resp.workspace_id
      r['worker_addr'] = resp.worker_addr
      r['daemon_module'] = resp.rsync_dest.daemon_module

    # Create a container on the worker.
    sys.stdout.write('Setting up the container... ')
    sys.stdout.flush()
    try:
      with grpc_helper.get_channel(resp.worker_addr) as ch:
        worker = worker_client.create_authed_client(ch, self._local_cfg)
        worker.init()
      sys.stdout.write('Done.\n')
      print('\nDone setting up rx! To use, run:\n\n\t$ rx <your command>\n')
      return 0
    except worker_client.WorkerError as e:
      raise TrexError(f'Error setting up worker {resp.worker_addr}: {e}', -1)

  def subscribe(self) -> bool:
    if not payment.explain_subscription(self._local_cfg.cwd):
      return False
    # Get the link for payment.
    req = empty_pb2.Empty()
    response = self._stub.GetSubscribeInfo(req, metadata=self._metadata)
    payment.open_browser(response.subscribe_info)
    self._wait_for_payment()
    return True

  def stop(self, workspace_id: str):
    req = rx_pb2.StopRequest(workspace_id=workspace_id, save=True)
    def get_progress(
        resp: Iterable[rx_pb2.StopResponse]
    ) -> Generator[rx_pb2.DockerImageProgress, None, None]:
      for r in resp:
        yield r.push_progress
    resp = self._stub.Stop(req, metadata=self._metadata)
    result = progress_bar.show_progress_bars(get_progress(resp))
    if result and result.code != 0:
      raise TrexError('Error stopping worker', result)

  def unsubscribe(self):
    req = empty_pb2.Empty()
    response = self._stub.Unsubscribe(req, metadata=self._metadata)
    if response.result.code != rx_pb2.OK:
      raise TrexError(response.result.message, response.result.code)

  def _wait_for_payment(self):
    end = datetime.datetime.now() + _PAYMENT_TIMEOUT
    sys.stdout.write('Waiting for subscription to be activated...')
    while datetime.datetime.now() < end:
      sys.stdout.write('.')
      sys.stdout.flush()
      response = self._stub.CheckSubscription(
        empty_pb2.Empty(), metadata=self._metadata)
      if response.result.code == rx_pb2.OK:
        payment.success()
        return
      if response.result.code != rx_pb2.SUBSCRIPTION_REQUIRED:
        # Something else went wrong.
        raise TrexError(response.result.message, response.result.code)
      # Otherwise, we're just waiting for them to finish subscribing.
      time.sleep(_SLEEP_SECS)
    raise TimeoutError(
      'Timed out waiting for subscription to activate. Please run the command '
      'again after subscribing.')

  def _create_username(self, email: str) -> str:
    username = user.username_prompt(email)
    req = rx_pb2.SetUsernameRequest(username=username)
    try:
      resp = self._stub.SetUsername(
        req, metadata=self._metadata, timeout=_RPC_TIMEOUT_SECS)
    except grpc.RpcError as e:
      e = cast(grpc.Call, e)
      raise TrexError(f'Could not set username: {e.details()}', -1)
    if resp.result.code == rx_pb2.INVALID:
      raise TrexError(
        f'{resp.result.message}\nInvalid username: {username}', rx_pb2.INVALID)
    return username

  def _get_username(self, email: str) -> str:
    # Check with rx server.
    username = self._get_username_from_rx()
    if username:
      return username

    # Prompt the user to choose a username.
    return self._create_username(email)

  def _get_username_from_rx(self) -> str:
    try:
      resp = self._stub.GetUser(
        empty_pb2.Empty(), metadata=self._metadata, timeout=_RPC_TIMEOUT_SECS)
    except grpc.RpcError as e:
      e = cast(grpc.Call, e)
      raise TrexError(f'Could not get user from rx: {e.details()}', -1)
    return resp.username

  def _run_initial_rsync(self, remote_cfg: remote.Remote):
    r = rsync.RsyncClient(self._local_cfg, remote_cfg)
    return_code = r.to_remote()
    if return_code == 0:
      logging.info('Copied files to %s', r.host)


class TrexError(RuntimeError):
  """Class to repackage any init errors that happen and add an exit code."""

  def __init__(self, message, code, *args):
    super().__init__(message, *args)
    self._code = code

  @property
  def code(self):
    return self._code


def create_authed_client(ch: grpc.Channel, local_cfg: local.LocalConfig):
  lm = login.LoginManager(local_cfg.cwd)
  lm.login()
  return Client(ch, local_cfg, lm.grpc_metadata)

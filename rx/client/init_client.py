import sys

from absl import logging
from google.protobuf import empty_pb2
import grpc

from rx.client import grpc_helper
from rx.client import login
from rx.client import rsync
from rx.client import user
from rx.client.configuration import local
from rx.client.configuration import remote
from rx.proto import rx_pb2
from rx.proto import rx_pb2_grpc

_TIMEOUT = 10

class Client():
  """Handle contacting the remote server."""

  def __init__(self, channel: grpc.Channel, local_cfg: local.LocalConfig):
    self._stub = rx_pb2_grpc.SetupServiceStub(channel)
    self._local_cfg = local_cfg
    self._login = login.LoginManager()
    self._metadata = local.get_grpc_metadata()

  def create_user_or_log_in(self) -> user.User:
    # First, make sure we're logged in with Google.
    try:
      self._login.login()
    except login.AuthError as e:
      raise InitError(e, -1)
    self._metadata += self._login.grpc_metadata
    email = self._login.id_token['email']

    # Check if user is set up.
    # TODO: it would be better to read the username from the config and
    # automatically try to set it on the remote. However, this generally
    # shouldn't come up for normal users.
    username = self._get_username()
    if not user.has_config(self._local_cfg.cwd):
      with user.CreateUser(self._local_cfg.cwd) as c:
        c['username'] = username
        c['email'] = email
    return user.User(self._local_cfg.cwd, email)

  def init(self) -> int:
    try:
      target_env = self._local_cfg.get_target_env()
    except local.ConfigError as e:
      raise InitError(str(e), -1)
    if target_env.alloc.hardware.processor == 'gpu':
      print('rx only works with CPUs at the moment, but I appreciate your '
            'enthusiasm! Try setting --remote=python-cpu for now.')
      return -1
    req = rx_pb2.InitRequest(
      project_name=self._local_cfg['project_name'],
      rsync_source=self._local_cfg.rsync_source,
      target_env=target_env,
    )
    sys.stdout.write('Finding a remote worker... ')
    sys.stdout.flush()
    try:
      # Five minute timeout.
      resp = self._stub.Init(req, metadata=self._metadata, timeout=(5 * 60))
      sys.stdout.write('Done.\n')
    except grpc.RpcError as e:
      raise InitError(f'Could not initialize worker: {e.details()}', -1)
    if resp.result.code != 0:
      raise InitError(resp.result.message, -1)

    # TODO: create a threaded UserStatus class with __enter__/__exit__.
    sys.stdout.write('Copying source code... ')
    sys.stdout.flush()
    with remote.WritableRemote(self._local_cfg.cwd) as r:
      r['workspace_id'] = resp.workspace_id
      r['worker_addr'] = resp.worker_addr
      r['grpc_addr'] = f'{resp.worker_addr}'
      r['daemon_module'] = resp.rsync_dest.daemon_module
    self._run_initial_rsync()
    sys.stdout.write('Done.\n')
    self._install_deps(f'{resp.worker_addr}', resp.workspace_id)
    print('\nDone setting up rx! To use, run:\n\n\t$ rx <your command>\n')
    return 0

  def _create_username(self) -> str:
    username = user.username_prompt(self._login.id_token['email'])
    req = rx_pb2.SetUsernameRequest(username=username)
    try:
      resp = self._stub.SetUsername(
        req, metadata=self._metadata, timeout=_TIMEOUT)
    except grpc.RpcError as e:
      raise InitError(f'Could not set username: {e.details()}', -1)
    if resp.result.code == rx_pb2.INVALID:
      raise InitError(
        f'{resp.result.message}\nInvalid username: {username}', rx_pb2.INVALID)
    return username

  def _get_username(self) -> str:
    # Check with rx server.
    username = self._get_username_from_rx()
    if username:
      return username

    # Prompt the user to choose a username.
    return self._create_username()

  def _get_username_from_rx(self) -> str:
    try:
      resp = self._stub.GetUser(
        empty_pb2.Empty(), metadata=self._metadata, timeout=_TIMEOUT)
    except grpc.RpcError as e:
      raise InitError(f'Could not get user from rx: {e.details()}', -1)
    return resp.username

  def _run_initial_rsync(self):
    self._rsync = rsync.RsyncClient(
      self._local_cfg, remote.Remote(self._local_cfg.cwd))
    return_code = self._rsync.to_remote()
    if return_code == 0:
      logging.info('Copied files to %s', self._rsync.host)

  def _install_deps(self, grpc_addr: str, workspace_id: str) -> int:
    channel = grpc_helper.get_channel(grpc_addr)
    stub = rx_pb2_grpc.ExecutionServiceStub(channel)
    req = rx_pb2.InstallDepsRequest(workspace_id=workspace_id)
    resp = None
    try:
      for resp in stub.InstallDeps(
        req, metadata=self._metadata, timeout=(10 * 60)):
        if resp.stdout:
          sys.stdout.buffer.write(resp.stdout)
          sys.stdout.buffer.flush()
    except grpc.RpcError as e:
      raise InitError(e.details(), -1)
    if resp and resp.HasField('result') and resp.result.code:
      raise InitError(resp.result.message, resp.result.code)
    return 0


class InitError(RuntimeError):
  """Class to repackage any init errors that happen and add an exit code."""

  def __init__(self, message, code, *args):
    super().__init__(message, *args)
    self._code = code

  @property
  def code(self):
    return self._code

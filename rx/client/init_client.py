import sys

from absl import logging
import grpc

from rx.client import login
from rx.client import rsync
from rx.client import user
from rx.client.configuration import config_base
from rx.client.configuration import local
from rx.client.configuration import remote
from rx.proto import rx_pb2
from rx.proto import rx_pb2_grpc


class Client():
  """Handle contacting the remote server."""

  def __init__(self, local_cfg: local.LocalConfig):
    grpc_addr = config_base.GRPC_HOST.value
    if config_base.is_local():
      channel = grpc.insecure_channel(grpc_addr)
    else:
      channel = grpc.secure_channel(
        grpc_addr, credentials=grpc.ssl_channel_credentials())
    self._stub = rx_pb2_grpc.SetupServiceStub(channel)
    self._local_cfg = local_cfg
    self._login = login.LoginManager()
    self._metadata = local.get_grpc_metadata()

  def create_user_or_log_in(self) -> user.User:
    # First, make sure we're logged in with Google.
    self._login.login()
    self._metadata += self._login.grpc_metadata
    email = self._login.id_token['email']

    # Check if user is set up.
    if not user.has_config(self._local_cfg.cwd):
      with user.CreateUser(self._local_cfg.cwd) as c:
        c['username'] = self._get_username()
        c['email'] = email
    return user.User(self._local_cfg.cwd, email)

  def init(self) -> int:
    # TODO: support GPUs.
    target_env = self._local_cfg.get_target_env()
    if target_env.alloc.hardware.processor == 'gpu':
      print('rx only works with CPUs at the moment, but I appreciate your '
            'enthusiasm! Try setting --remote=python-cpu for now.')
      return -1
    req = rx_pb2.InitRequest(
      rsync_source=self._local_cfg.rsync_source,
      target_env=target_env,
    )
    try:
      resp = self._stub.Init(req, metadata=self._metadata)
    except grpc.RpcError as e:
      sys.stderr.write(e.details())
      return -1
    if resp.result.code != 0:
      sys.stderr.write(resp.result.message)
      return -1

    with remote.WritableRemote(self._local_cfg.cwd) as r:
      r['workspace_id'] = resp.workspace_id
      r['worker_addr'] = resp.worker_addr
      r['grpc_addr'] = f'{resp.worker_addr}:50051'
      r['daemon_module'] = resp.rsync_dest.daemon_module
    self._run_initial_rsync()
    return self._install_deps(f'{resp.worker_addr}:50051', resp.workspace_id)

  def _create_username(self) -> str:
    username = user.username_prompt(self._login.id_token['email'])
    req = rx_pb2.SetUsernameRequest(username=username)
    try:
      resp = self._stub.SetUsername(req, metadata=self._metadata)
    except grpc.RpcError as e:
      sys.stderr.write(e.details())
      raise e
    if resp.result.code == rx_pb2.INVALID:
      sys.stderr.write(resp.result.message)
      raise RuntimeError(f'Invalid username: {username}')
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
      resp = self._stub.GetUser(rx_pb2.EmptyMessage(), metadata=self._metadata)
    except grpc.RpcError as e:
      sys.stderr.write(e.details())
      raise e
    return resp.username

  def _run_initial_rsync(self):
    self._rsync = rsync.RsyncClient(
      self._local_cfg.cwd, remote.Remote(self._local_cfg.cwd))
    return_code = self._rsync.to_remote()
    if return_code == 0:
      logging.info('Copied files to %s', self._rsync.host)

  def _install_deps(self, grpc_addr: str, workspace_id: str) -> int:
    channel = grpc.insecure_channel(grpc_addr)
    stub = rx_pb2_grpc.ExecutionServiceStub(channel)
    req = rx_pb2.InstallDepsRequest(workspace_id=workspace_id)
    try:
      resp = stub.InstallDeps(req, metadata=self._metadata)
    except grpc.RpcError as e:
      sys.stderr.write(e.details())
      return -1
    if resp.result.code:
      sys.stderr.write(resp.result.message)
    return resp.result.code

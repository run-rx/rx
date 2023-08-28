import os
import pathlib
import sys
from typing import Generator, Iterable, List, Optional, Tuple, cast

from absl import flags
from absl import logging
import grpc

from rx.client import login
from rx.client import output_handler
from rx.client import payment
from rx.client.configuration import local
from rx.client.configuration import remote
from rx.client.worker import executor
from rx.client.worker import progress_bar
from rx.client.worker import rsync
from rx.proto import rx_pb2
from rx.proto import rx_pb2_grpc

SIGINT_CODE = 130

# TODO: set up UI for looking at previous executions.
_BASE_URI = 'https://la-brea.run-rx.com'
_NOT_REACHABLE = 1

_CWD = flags.DEFINE_string('cwd', None, 'Directory to run the command from')

class Client:
  """Handle contacting the remote server."""

  def __init__(
      self,
      channel: grpc.Channel,
      local_cfg: local.LocalConfig,
      auth_metadata: Tuple[Tuple[str, str]]):
    self._local_cfg = local_cfg
    self._remote_cfg = remote.Remote(local_cfg.cwd)
    self._rsync = rsync.RsyncClient(local_cfg, self._remote_cfg)
    self._stub = rx_pb2_grpc.ExecutionServiceStub(channel)
    self._metadata = local.get_grpc_metadata() + auth_metadata
    self._current_execution_id = None

  def init(self):
    # Get the container downloaded/running.
    req = rx_pb2.WorkerInitRequest(workspace_id=self._remote_cfg.workspace_id)
    resp = self._stub.Init(req, metadata=self._metadata)
    def get_progress(
        resp: Iterable[rx_pb2.WorkerInitResponse]
    ) -> Generator[rx_pb2.DockerImageProgress, None, None]:
      for r in resp:
        if r.pull_progress:
          yield r.pull_progress
    result = progress_bar.show_progress_bars(get_progress(resp))
    if result and result.code != 0:
      raise WorkerError(
        f'Error initializing worker {self._remote_cfg.worker_addr}', result)

    # Sync sources.
    result = self._rsync.to_remote()
    if result != 0:
      raise UnreachableError()

    # Install deps.
    self._install_deps()

  def exec(self, argv: List[str]) -> int:
    cmd_str = ' '.join(argv)
    logging.info(f'Running `{cmd_str}` on {self._remote_cfg.worker_addr}')

    result = self._rsync.to_remote()
    if result != 0:
      raise UnreachableError()

    rxroot = os.path.abspath(self._local_cfg.cwd)
    cwd = os.path.abspath(pathlib.Path.cwd())
    if is_subdir(parent=rxroot, child=cwd):
      cwd = str(pathlib.Path.cwd().relative_to(self._local_cfg.cwd))
    else:
      cwd = _CWD.value

    out_handler = output_handler.OutputHandler(self._local_cfg.cwd)

    request = rx_pb2.ExecRequest(
      workspace_id=self._remote_cfg.workspace_id, argv=argv, cwd=cwd)
    runner = executor.Executor(self._stub, request)
    try:
      response = runner.run(self._metadata)
    except grpc.RpcError as e:
      e = cast(grpc.Call, e)
      sys.stderr.write(f'Error contacting {self._remote_cfg.worker_addr}: {e.details()}\n')
      return _NOT_REACHABLE
    except KeyboardInterrupt:
      self.maybe_kill()
      return SIGINT_CODE
    except RuntimeError as e:
      # Bug in grpc, probably.
      msg = str(e)
      if msg == 'cannot release un-acquired lock':
        self.maybe_kill()
        return SIGINT_CODE
      else:
        sys.stderr.write(msg)
        return -1

    out_handler.write_outputs(self._rsync)

    if (response is not None and response.HasField('result') and
        response.result.code != 0):
      if response.result.code == rx_pb2.SUBSCRIPTION_REQUIRED:
        payment.request_subscription(self._local_cfg.cwd)
        return 0
      sys.stderr.write(f'{response.result.message}\n')
      return response.result.code
    return 0

  def maybe_kill(self):
    """Kill the process, if it exists."""
    if self._current_execution_id is None:
      logging.error('No ID to kill.')
      return

    req = rx_pb2.KillRequest(
      workspace_id=self._remote_cfg.workspace_id,
      execution_id=self._current_execution_id,
    )
    self._stub.Kill(req, metadata=self._metadata)

  def stop(self):
    req = rx_pb2.StopRequest(
      workspace_id=self._remote_cfg.workspace_id, save=True)
    def get_progress(
        resp: Iterable[rx_pb2.StopResponse]
    ) -> Generator[rx_pb2.DockerImageProgress, None, None]:
      for r in resp:
        yield r.push_progress
    resp = self._stub.Stop(req, metadata=self._metadata)
    result = progress_bar.show_progress_bars(get_progress(resp))
    if result and result.code != 0:
      raise WorkerError('Error stopping worker', result)

  def _install_deps(self):
    req = rx_pb2.InstallDepsRequest(workspace_id=self._remote_cfg.workspace_id)
    resp = None
    try:
      for resp in self._stub.InstallDeps(
        req, metadata=self._metadata, timeout=(10 * 60)):
        if resp.stdout:
          sys.stdout.buffer.write(resp.stdout)
          sys.stdout.buffer.flush()
    except grpc.RpcError as e:
      e = cast(grpc.Call, e)
      raise WorkerError(e.details(), result=None)
    if resp and resp.HasField('result') and resp.result.code:
      raise WorkerError(message=None, result=resp.result)


def create_authed_client(ch: grpc.Channel, local_cfg: local.LocalConfig):
  lm = login.LoginManager(local_cfg.cwd)
  lm.login()
  return Client(ch, local_cfg, lm.grpc_metadata)


def is_subdir(*, parent: str, child: str) -> bool:
  return os.path.commonpath([parent]) == os.path.commonpath([parent, child])


class WorkerError(RuntimeError):
  def __init__(
      self,
      message: Optional[str],
      result: Optional[rx_pb2.Result],
      *args: object):
    """Allow passing message, result, or both."""
    full_message = message
    if message is not None and result is not None:
      full_message = f'{message}: {result.message}'
    elif result is not None:
      full_message = result.message
    super().__init__(full_message, *args)
    self.code = result.code if result is not None else -1


class UnreachableError(WorkerError):
  def __init__(self, *args: object):
    super().__init__('unreachable', None, *args)

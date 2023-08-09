
import os
import pathlib
import sys
from typing import List, Tuple, cast

from absl import flags
from absl import logging
import grpc
import tqdm

from rx.client import login
from rx.client import output_handler
from rx.client.configuration import local
from rx.client.configuration import remote
from rx.client.worker import executor
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
    progress_bars = {}
    try:
      for resp in self._stub.Init(req, metadata=self._metadata):
        if resp.result.code != 0:
          raise InitError(
            f'Error initializing worker {self._remote_cfg.worker_addr}: '
            f'{resp.result.message}')
        if resp.pull_progress:
          pp = resp.pull_progress
          if pp.id not in progress_bars:
            # First item must have a total.
            if pp.total == 0:
              continue
            progress_bars[pp.id] = ProgressBar(pp)
          progress_bars[pp.id].update(pp)
    except grpc.RpcError as e:
      e = cast(grpc.Call, e)
      raise InitError(
        f'Error initializing worker {self._remote_cfg.worker_addr}: '
        f'{e.details()}')
    for p in progress_bars.values():
      p.close()

    # Sync sources.
    result = self._rsync.to_remote()
    if result != 0:
      raise UnreachableError(self._remote_cfg.worker_addr, result)

    # Install deps.
    self._install_deps()

  def exec(self, argv: List[str]) -> int:

    cmd_str = ' '.join(argv)
    logging.info(f'Running `{cmd_str}` on {self._remote_cfg.worker_addr}')

    result = self._rsync.to_remote()
    if result != 0:
      raise UnreachableError(self._remote_cfg.worker_addr, result)

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
      raise InitError(e.details(), -1)
    if resp and resp.HasField('result') and resp.result.code:
      raise InitError(resp.result.message, resp.result.code)


def create_authed_client(ch: grpc.Channel, local_cfg: local.LocalConfig):
  lm = login.LoginManager(local_cfg.cwd)
  lm.login()
  return Client(ch, local_cfg, lm.grpc_metadata)


def is_subdir(*, parent: str, child: str) -> bool:
  return os.path.commonpath([parent]) == os.path.commonpath([parent, child])


class ProgressBar:

  def __init__(self, pp: rx_pb2.DockerImagePullProgress) -> None:
    assert pp.total > 0
    self._bar = tqdm.tqdm(
      desc=f'{pp.status} layer {pp.id}',
      total=pp.total,
      unit=' bytes')
    self._is_done = False

  def close(self):
    self._bar.close()

  def update(self, pp: rx_pb2.DockerImagePullProgress):
    if pp.total == 0:
      self._bar.set_description(f'{pp.status} layer {pp.id}')
      return
    if self._is_done:
      return

    # Note: this jumps back to 0 for download -> extract, which is good?
    self._bar.update(pp.current - self._bar.n)
    if self._bar.n == pp.total:
      self._is_done = True


# TODO: this needs to take code.
class InitError(RuntimeError):
  pass

class UnreachableError(RuntimeError):
  def __init__(self, worker_addr: str, code: int, *args: object) -> None:
    super().__init__(*args)
    self.worker = worker_addr
    self.code = code

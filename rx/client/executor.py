import sys
from typing import List

from absl import logging
import grpc

from rx.client import login
from rx.client import output_handler
from rx.client import rsync
from rx.client.configuration import local
from rx.client.configuration import remote
from rx.proto import rx_pb2
from rx.proto import rx_pb2_grpc

SIGINT_CODE = 130

# TODO: set up UI for looking at previous executions.
_BASE_URI = 'https://la-brea.run-rx.com'
_NOT_REACHABLE = 1


class Client():
  """Handle contacting the remote server."""

  def __init__(
      self,
      channel: grpc.Channel,
      local_cfg: local.LocalConfig,
      remote_cfg: remote.Remote):
    self._uri = remote_cfg['grpc_addr']
    self._rsync = rsync.RsyncClient(local_cfg, remote_cfg)
    self._stub = rx_pb2_grpc.ExecutionServiceStub(channel)
    self._metadata = local.get_grpc_metadata()
    self._local_cfg = local_cfg
    self._remote_cfg = remote_cfg
    self._login = login.LoginManager()
    self._current_execution_id = None

  def exec(self, argv: List[str]) -> int:
    cmd_str = ' '.join(argv)
    logging.info(f'Running `{cmd_str}` on {self._uri}')

    self._login.login()
    self._metadata += self._login.grpc_metadata

    result = self._rsync.to_remote()
    if result != 0:
      print('Worker was unrechable, run `rx init` to get a new instance.')
      return result
    result = None

    request = rx_pb2.ExecRequest(
      workspace_id=self._remote_cfg['workspace_id'],
      argv=argv,
      rsync_source=self._local_cfg.rsync_source)

    out_handler = output_handler.OutputHandler()
    response = None
    try:
      for response in self._stub.Exec(request, metadata=self._metadata):
        self._current_execution_id = response.execution_id
        out_handler.handle(response)
    except grpc.RpcError as e:
      sys.stderr.write(f'Error contacting {self._uri}: {e.details()}\n')
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
      workspace_id=self._remote_cfg['workspace_id'],
      execution_id=self._current_execution_id,
    )
    self._stub.Kill(req, metadata=self._metadata)

from typing import List

from absl import logging
import grpc

from rx.client import grpc_helper
from rx.client import login
from rx.client import output_handler
from rx.client import rsync
from rx.client.configuration import local
from rx.client.configuration import remote
from rx.proto import rx_pb2
from rx.proto import rx_pb2_grpc

# TODO: set up UI for looking at previous executions.
_BASE_URI = 'https://la-brea.run-rx.com'
_NOT_REACHABLE = 1


class Client():
  """Handle contacting the remote server."""

  def __init__(self, local_cfg: local.LocalConfig):
    remote_cfg = remote.Remote(local_cfg.cwd)
    self._rsync = rsync.RsyncClient(local_cfg.cwd, remote_cfg)
    self._uri = remote_cfg['grpc_addr']
    channel = grpc_helper.get_channel(self._uri)
    self._stub = rx_pb2_grpc.ExecutionServiceStub(channel)
    self._metadata = local.get_grpc_metadata()
    self._local_cfg = local_cfg
    self._login = login.LoginManager()

  def exec(self, argv: List[str]) -> int:
    cmd_str = ' '.join(argv)
    logging.info(f'Running `{cmd_str}` on {self._uri}')

    self._login.login()
    self._metadata += self._login.grpc_metadata

    result = self._rsync.to_remote()
    if result != 0:
      return result
    result = None

    request = rx_pb2.ExecRequest(
      workspace_id=self._rsync.workspace_id,
      argv=argv,
      rsync_source=self._local_cfg.rsync_source)

    out_handler = output_handler.OutputHandler()
    response = None
    try:
      for response in self._stub.Exec(request, metadata=self._metadata):
        out_handler.handle(response)
    except grpc.RpcError as e:
      logging.error(f'Error contacting {self._uri}: {e.details()}')
      return _NOT_REACHABLE

    out_handler.write_outputs(self._rsync)

    if (response is not None and response.HasField('result') and
        response.result.code != 0):
      logging.error(response.result.message)
      return response.result.code
    return 0

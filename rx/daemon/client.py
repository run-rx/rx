"""rx command daemon client."""
import grpc
from typing import Dict, Optional, cast

from google.protobuf import empty_pb2

from rx.client.configuration import local
from rx.proto import daemon_pb2
from rx.proto import daemon_pb2_grpc
from rx.proto import rx_pb2


class Client:
  """Handle contacting the local daemon."""

  def __init__(self, channel: grpc.Channel, local_cfg: local.LocalConfig):
    self._local_cfg = local_cfg
    self._stub = daemon_pb2_grpc.PortForwardingServiceStub(channel)

  def close_port(self, port: int):
    req = daemon_pb2.OpenPortRequest(port=port)
    try:
      resp: rx_pb2.GenericResponse = self._stub.ClosePort(req)
    except grpc.RpcError as e:
      e = cast(grpc.Call, e)
      raise DaemonUnavailable(e.details())
    if resp.result.code != 0:
      raise PortError(resp.result.message)

  def info(self) -> Dict[int, int]:
    try:
      resp: daemon_pb2.GetPortsResponse = self._stub.GetPorts(empty_pb2.Empty())
    except grpc.RpcError as e:
      e = cast(grpc.Call, e)
      raise DaemonUnavailable(e.details())
    result = {}
    for p in resp.ports:
      result[p.port] = p.local_port
    return result

  def open_port(self, port: int, local_port: Optional[int] = None):
    req = daemon_pb2.OpenPortRequest(port=port)
    if local_port:
      req.local_port = local_port
    try:
      resp: rx_pb2.GenericResponse = self._stub.OpenPort(req)
    except grpc.RpcError as e:
      e = cast(grpc.Call, e)
      raise DaemonUnavailable(e.details())
    if resp.result.code != 0:
      raise PortError(resp.result.message)

  def is_running(self) -> bool:
    if not self._local_cfg.get_daemon_pid_file().exists():
      return False
    try:
      self.info()
    except DaemonUnavailable:
      return False
    return True


class DaemonUnavailable(RuntimeError):
  """Raised if the daemon is not reachable."""


class PortError(RuntimeError):
  """Raised if there is an issue forwarding ports."""

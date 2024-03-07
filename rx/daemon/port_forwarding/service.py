from typing import Dict

from absl import logging
import grpc
from google.protobuf import empty_pb2

from rx.client.configuration import local
from rx.client.configuration import remote
from rx.proto import rx_pb2
from rx.proto import daemon_pb2
from rx.proto import daemon_pb2_grpc
from rx.daemon.port_forwarding import port_forwarder


class PortForwardingService(daemon_pb2_grpc.PortForwardingServiceServicer):

  def __init__(self, local_cfg: local.LocalConfig) -> None:
    super().__init__()
    self._local_cfg = local_cfg
    self._remote_cfg = remote.Remote(self._local_cfg.cwd)
    self._ports: Dict[int, port_forwarder.PortForwarder] = {}

  def close_ports(self):
    """Clean up sockets on close."""
    for pf in self._ports.values():
      pf.stop()
    self._ports = {}

  def GetPorts(
      self, request: empty_pb2.Empty, context: grpc.ServicerContext,
  ) -> daemon_pb2.GetPortsResponse:
    del request
    del context
    response = daemon_pb2.GetPortsResponse(result=rx_pb2.Result())
    for p, pf in self._ports.items():
      port = response.ports.add()
      port.port = p
      if pf.local_port != p:
        port.local_port = pf.local_port
    return response

  def OpenPort(
      self, request: daemon_pb2.OpenPortRequest, context: grpc.ServicerContext,
  ) -> rx_pb2.GenericResponse:
    del context
    local_port = request.local_port if request.local_port else request.port
    if local_port in self._ports:
      return rx_pb2.GenericResponse(
        result=rx_pb2.Result(
          code=rx_pb2.EADDRINUSE,
          message=f'Already forwarding port {local_port}',
        )
      )
    pf = port_forwarder.PortForwarder(local_port, request.port)
    try:
      pf.start()
    except port_forwarder.AlreadyBoundError as e:
      return rx_pb2.GenericResponse(
        result=rx_pb2.Result(
          code=rx_pb2.EADDRINUSE, message=str(e),
        )
      )
    self._ports[local_port] = pf
    logging.info('Opened port %s', local_port)
    return rx_pb2.GenericResponse(result=rx_pb2.Result())

  def ClosePort(
      self, request: daemon_pb2.ClosePortRequest, context: grpc.ServicerContext,
  ) -> rx_pb2.GenericResponse:
    del context
    port = request.port
    if port not in self._ports:
      return rx_pb2.GenericResponse(
        result=rx_pb2.Result(
          code=rx_pb2.NOT_FOUND,
          message=f'Port {port} not forwarded',
        ),
      )
    self._ports[port].stop()
    logging.info('Closed port %s', port)
    return rx_pb2.GenericResponse(result=rx_pb2.Result())

import os
from typing import Callable, Iterable, Tuple

from absl import logging
import grpc

from rx.client.configuration import local


class VersionCheck(grpc.ServerInterceptor):
  """Make sure the daemon is up-to-date."""

  def intercept_service(
      self,
      continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler],
      handler_call_details: grpc.HandlerCallDetails
  ) -> grpc.RpcMethodHandler:
    client_version = get_metadata(handler_call_details, 'cv')
    if local.VERSION != client_version:
      def d(_, context: grpc.ServicerContext):
        context.send_initial_metadata((('pid', f'{os.getpid()}'),))
        context.abort(
          grpc.StatusCode.FAILED_PRECONDITION,
          f'Daemon is running version {local.VERSION}, expected '
          f'{client_version}')
      logging.info('Wrong version: %s vs %s', local.VERSION, client_version)
      return grpc.unary_unary_rpc_method_handler(d)
    return continuation(handler_call_details)


class PidCheck(grpc.ServerInterceptor):
  """Make sure we're connecting to the daemon we think we are."""

  def intercept_service(
      self,
      continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler],
      handler_call_details: grpc.HandlerCallDetails
  ) -> grpc.RpcMethodHandler:
    expected_pid = get_metadata(handler_call_details, 'pid')
    my_pid = f'{os.getpid()}'
    if my_pid != expected_pid:
      def d(_, context: grpc.ServicerContext):
        context.send_initial_metadata((('pid', my_pid),))
        context.abort(
          grpc.StatusCode.FAILED_PRECONDITION,
          f'Daemon has pid {my_pid}, expected {expected_pid}')
      logging.info('Wrong pid: %s vs %s', my_pid, expected_pid)
      return grpc.unary_unary_rpc_method_handler(d)
    return continuation(handler_call_details)


def get_metadata(
    handler_call_details: grpc.HandlerCallDetails, field: str) -> str:
  # HandlerCallDetails is actually a named tuple defined in grpc._server.
  metadata: Iterable[Tuple[str, str]] = handler_call_details.invocation_metadata
  for m in metadata:
    if m[0] == field:
      return m[1]
  raise RuntimeError(f'"{field}" not found in request')

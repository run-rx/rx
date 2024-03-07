from concurrent import futures
import os
import signal
import tempfile
from typing import Sequence

from absl import app
from absl import flags
from absl import logging
import grpc

from rx.client.configuration import local
from rx.daemon import daemon
from rx.daemon import interceptors
from rx.daemon.port_forwarding import service
from rx.proto import daemon_pb2_grpc

# Only allow local connections.
_BIND_ADDR = '127.0.0.1'
_PORT = flags.DEFINE_integer(
  'port', local.DEFAULT_DAEMON_PORT, 'The port to listen on.')


def _configure_logging():
  handler = logging.get_absl_handler()
  assert handler
  handler.python_handler.use_absl_log_file(
    program_name='rx-daemon', log_dir=tempfile.gettempdir())
  logging.info('Starting rx daemon with pid %s', os.getpid())


def _start_server(port: int, local_cfg: local.LocalConfig):
  addr = f'{_BIND_ADDR}:{port}'
  server = grpc.server(
    futures.ThreadPoolExecutor(max_workers=10),
    interceptors=(interceptors.PidCheck(), interceptors.VersionCheck()),
    # By default grpc allows multiple servers to listen on the same port. Turn
    # off that behavior.
    options=(('grpc.so_reuseport', 0),),
  )
  try:
    server.add_insecure_port(addr)
  except RuntimeError as e:
    if 'Failed to bind' in str(e):
      logging.exception(
        f'Could not bind to localhost:{port}, is something already running '
        'on that port?')
    else:
      logging.exception('Unknown error')
    return
  handler = service.PortForwardingService(local_cfg)
  daemon_pb2_grpc.add_PortForwardingServiceServicer_to_server(handler, server)
  signal.signal(signal.SIGINT, get_signal_handler(handler, server))
  server.start()
  logging.info(f'Listening on {addr}')
  server.wait_for_termination()


def get_signal_handler(pf: service.PortForwardingService, server: grpc.Server):
  def cleanup(signum: int, frame):
    del signum
    del frame
    pf.close_ports()
    server.stop(grace=None)
  return cleanup


def start_daemon():
  local_cfg = local.get_local_config()
  # TODO: add a signal handler to stop the daemon.
  with daemon.Daemonizer(local_cfg.cwd):
    _configure_logging()
    _start_server(_PORT.value, local_cfg)
  logging.info('Exiting.')


def main(argv: Sequence[str]):
  del argv
  start_daemon()


# Called by rx-daemon binary.
def run():
  app.run(main)


if __name__ == '__main__':
  run()

"""Port forwarding."""
import errno
import queue
import socket
import threading
import time

from absl import logging

from rx.client import grpc_helper
from rx.client import worker_client
from rx.client.configuration import local
from rx.client.configuration import remote
from rx.daemon.port_forwarding import client_socket

_LOCALHOST = '127.0.0.1'


class PortForwarder:
  """Forwards a port."""

  def __init__(self, local_port: int, remote_port: int) -> None:
    self.local_port = local_port
    self._remote_port = remote_port
    self._local_config = local.get_local_config()
    self._worker_addr = remote.Remote(self._local_config.cwd).worker_addr
    self._done = False
    # This is the socket that the server listens on.
    self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    self._request_queue = queue.SimpleQueue()
    self._done_with_requests = threading.Event()
    self._response_queue = queue.SimpleQueue()
    self._done_with_responses = threading.Event()

  def run_forever(self):
    # Basic flow:
    # * Create client socket to accept a connection
    # * Write client request to queue
    # * Send client request to remote machine
    # * Receive response from remote machine
    # * Send response to client socket
    while not self._done:
      # Outer loop repeatedly creates a new worker stub if it dies.
      try:
        with grpc_helper.get_channel(self._worker_addr) as ch:
          client = worker_client.create_authed_client(ch, self._local_config)
          while not self._done:
            # Inner loop repeatedly waits for client connections, reusing the
            # worker stub.
            self.accept_connection(client)
      except worker_client.DisconnectionError as e:
        logging.info('Disconnected from worker: %s', e)
        time.sleep(1)
      except worker_client.WorkerError as e:
        # Unknown error, exit.
        print(e)
        return

  def start(self):
    """Start listening on the port and kick off a thread to listen forever."""
    self._listen()
    th = threading.Thread(target=self.run_forever, daemon=True)
    th.start()

  def accept_connection(self, grpc_client: worker_client.Client):
    try:
      client_sock, _ = self._server_sock.accept()
    except ConnectionAbortedError:
      print('Connection aborted')
      return

    # Run handler on a separate thread so we can immediately start waiting for
    # connections again.
    th = threading.Thread(
      target=self._handle_request,
      args=(client_sock, grpc_client,),
      daemon=True)
    th.start()

  def stop(self):
    self._done = True
    self._server_sock.close()

  def _handle_request(
      self, client_sock: socket.socket, wc: worker_client.Client):
    with client_socket.Connection(client_sock) as conn:
      try:
        conn.handle(wc, self._remote_port)
      except worker_client.WorkerError:
        # If we don't explicitly log the exception, it seems to get swallowed
        # (probably because it's in a separate thread).
        logging.exception('Error forwarding request')
        return

  def _listen(self):
    try:
      self._server_sock.bind((_LOCALHOST, self.local_port))
    except OSError as e:
      if e.errno == errno.EADDRINUSE:
        raise AlreadyBoundError(
          f'Port {self.local_port} is already in use, cannot bind.')
      raise e
    self._server_sock.listen()
    print(f'Listening on {self.local_port}')

class AlreadyBoundError(RuntimeError):
  """Raised when the port is already in use."""

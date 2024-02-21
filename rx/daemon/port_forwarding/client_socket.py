import queue
import socket
import threading
import time
from types import TracebackType
from typing import Generator, Optional, Type

from absl import logging

from rx.client import worker_client

_FRAME_SIZE = 1024


class Connection:
  """Handles one client connection."""

  def __init__(self, client_sock: socket.socket) -> None:
    self._client_sock = client_sock

    self._request_queue = queue.SimpleQueue()
    self._done_with_requests = threading.Event()
    self._response_queue = queue.SimpleQueue()
    self._done_with_responses = threading.Event()

  def __enter__(self) -> 'Connection':
    # Start up a thread to forward data to the local socket as it arrives.
    return self

  def __exit__(self, exctype: Optional[Type[BaseException]],
             excinst: Optional[BaseException],
             exctb: Optional[TracebackType]):
    del exctype
    del excinst
    del exctb
    self._done_with_requests.set()
    self._done_with_responses.set()
    self._client_recv_thread.join()
    self._server_recv_thread.join()
    if self._client_sock:
      self._client_sock.close()

  def handle(self, grpc_client: worker_client.Client, remote_port: int):
    """Handles a client connection."""
    self._done_with_requests.clear()
    self._done_with_responses.clear()

    self._client_recv_thread = threading.Thread(target=self.recv_from_local)
    self._client_recv_thread.start()
    self._server_recv_thread = threading.Thread(target=self.remote_to_local)
    self._server_recv_thread.start()

    # Wait for requests to be sent.
    if self._has_requests():
      for resp in grpc_client.forward_to_port(
        remote_port, self._pull_from_req_queue()):
        if not resp:
          break
        self._response_queue.put(resp)
      self._done_with_responses.set()

      # Wait for responses to be sent.
      while self._response_queue.qsize() > 0:
        time.sleep(0)
    else:
      self._done_with_requests.set()
      self._done_with_responses.set()

    self._server_recv_thread.join()
    self._client_recv_thread.join()

  def _has_requests(self) -> bool:
    """Blocks until there is either something in the request queue or the
    connection is closed."""
    while not self._done_with_requests.is_set():
      if not self._request_queue.empty():
        return True
      time.sleep(0)
    return not self._request_queue.empty()

  def _pull_from_req_queue(self) -> Generator[bytes, None, None]:
    """Yield local requests."""
    while not self._done_with_requests.is_set():
      try:
        yield self._request_queue.get_nowait()
      except queue.Empty:
        time.sleep(0)

  def recv_from_local(self):
    """Receives bytes from the local sock and puts them in a queue."""
    # Wait for a client to make a request.
    try:
      while not self._done_with_requests.is_set():
        response = self._client_sock.recv(_FRAME_SIZE)
        if not response:
          break
        self._request_queue.put(response)
    except ConnectionResetError:
      logging.exception('Connection reset in recv')
    except OSError:
      logging.exception('Error in recv')
    finally:
      self._done_with_requests.set()

  def remote_to_local(self):
    """Sends bytes from the remote's queue to the local sock."""
    while (
        self._response_queue.qsize() > 0 or
        not self._done_with_responses.is_set()):
      time.sleep(0)
      try:
        buf = self._response_queue.get(timeout=0)
      except queue.Empty:
        continue
      x = 0
      while x < len(buf):
        assert self._client_sock
        x += self._client_sock.send(buf)

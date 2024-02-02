import errno
import fcntl
import os
import sys
import selectors
import termios
import threading
import tty
from types import TracebackType
from typing import Any, BinaryIO, Optional, Tuple, Type

from absl import logging

from rx.proto import rx_pb2
from rx.proto import rx_pb2_grpc
from rx.client import output_handler


class Executor:

  def __init__(
      self,
      stub: rx_pb2_grpc.ExecutionServiceStub,
      req: rx_pb2.ExecRequest) -> None:
    self._stub = stub
    self._request = req

  def run(
      self,
      metadata: Tuple[Tuple[str, Any], ...],
      out_handler: output_handler.OutputHandler,
  ) -> rx_pb2.ExecResponse:
    response = None
    with StdinIterator(self._request) as req_it:
      for response in self._stub.Exec(req_it, metadata=metadata):
        self.write(response.stdout, sys.stdout.buffer)
        self.write(response.stderr, sys.stderr.buffer)
        out_handler.handle(response)
    assert response
    return response

  def write(self, buf: bytes, sink: BinaryIO) -> None:
    if not buf:
      return
    written = 0
    while written < len(buf):
      try:
        written += sink.write(buf[written:])
        sink.flush()
      except BlockingIOError as e:
        if e.errno == errno.EAGAIN:
          continue
        logging.info(
          'Error writing at byte %s of %s to %s: %s', written, len(buf),
          sink.name, e)
        raise e


class StdinIterator:

  def __init__(self, request: rx_pb2.ExecRequest) -> None:
    self._running = True
    self._stdin_buffer = [request]
    self._stdin_avail = threading.Condition()
    self._original_flags = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
    self._original_attrs = termios.tcgetattr(sys.stdin)
    self._selector = selectors.DefaultSelector()

  def __enter__(self) -> 'StdinIterator':
    # This also sets O_NONBLOCK for stdout/stderr, as they are copied from
    # stdin.
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, self._original_flags | os.O_NONBLOCK)
    # Prevent echo of characters. This is unset by the termios.tcsetattr call in
    # __exit__.
    tty.setcbreak(sys.stdin)
    self._selector.register(sys.stdin, selectors.EVENT_READ, self.got_stdin)
    th = threading.Thread(target=self.loop, daemon=True)
    th.start()
    return self

  def __exit__(self, exctype: Optional[Type[BaseException]],
             excinst: Optional[BaseException],
             exctb: Optional[TracebackType]):
    self._selector.unregister(sys.stdin)
    termios.tcsetattr(sys.stdin, termios.TCSANOW, self._original_attrs)
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, self._original_flags)
    self._running = False
    return False

  def __next__(self) -> rx_pb2.ExecRequest:
    # This is probably unnecessary, nothing should call next once exec is done.
    if not self._running:
      raise StopIteration()
    with self._stdin_avail:
      while not self._stdin_buffer:
        if not self._running:
          raise StopIteration()
        self._stdin_avail.wait()
      return self._stdin_buffer.pop(0)

  def loop(self):

    while self._running:
      events = self._selector.select(timeout=0)
      for key, mask in events:
        del mask
        key.data()

  def got_stdin(self):
    stdin_str = sys.stdin.read()
    if stdin_str:
      with self._stdin_avail:
        self._stdin_buffer += [
          rx_pb2.ExecRequest(stdin=stdin_str.encode('utf-8'))]
        self._stdin_avail.notify()

import fcntl
import os
import sys
import selectors
import termios
import threading
import tty
from types import TracebackType
from typing import Any, Optional, Tuple, Type

from rx.proto import rx_pb2
from rx.proto import rx_pb2_grpc

STDOUT = 1
STDERR = 2


class Executor:

  def __init__(
      self,
      stub: rx_pb2_grpc.ExecutionServiceStub,
      req: rx_pb2.ExecRequest) -> None:
    self._stub = stub
    self._request = req

  def run(
      self, metadata: Tuple[Tuple[str, Any], ...]
  ) -> Optional[rx_pb2.ExecResponse]:
    response = None
    with StdinIterator(self._request) as req_it:
      for response in self._stub.Exec(req_it, metadata=metadata):
        self.write(response)
    return response

  def write(self, resp: rx_pb2.ExecResponse) -> None:
    if resp.stdout:
      sys.stdout.buffer.write(resp.stdout)
      sys.stdout.flush()
    if resp.stderr:
      sys.stderr.buffer.write(resp.stderr)
      sys.stderr.flush()


class StdinIterator:

  def __init__(self, request: rx_pb2.ExecRequest) -> None:
    self._initial_request = request
    self._running = True
    self._stdin_buffer = [request]
    self._stdin_avail = threading.Condition()
    self._original_attrs = termios.tcgetattr(sys.stdin)

  def __enter__(self) -> 'StdinIterator':
    orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)
    th = threading.Thread(target=self.loop, daemon=True)
    th.start()
    return self

  def __exit__(self, exctype: Optional[Type[BaseException]],
             excinst: Optional[BaseException],
             exctb: Optional[TracebackType]):
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._original_attrs)
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
    # Prevent echo of characters.
    tty.setcbreak(sys.stdin)

    sel = selectors.DefaultSelector()
    sel.register(sys.stdin, selectors.EVENT_READ, self.got_stdin)

    while self._running:
      events = sel.select(timeout=0)
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

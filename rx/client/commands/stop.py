import sys

from rx.client import grpc_helper
from rx.client import worker_client
from rx.client.commands import command
from rx.client.configuration import config_base

class StopCommand(command.Command):
  """Initialize (or reinitialize) the remote."""

  def run(self) -> int:
    try:
      with grpc_helper.get_channel(self.remote_config.worker_addr) as ch:
        client = worker_client.create_authed_client(ch, self.local_config)
        client.stop()
    except config_base.ConfigNotFoundError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return -1
    except worker_client.WorkerError as e:
      sys.stderr.write(f'{e}\n')
      sys.stderr.flush()
      return e.code
    return 0


if __name__ == '__main__':
  print('Call exec.')

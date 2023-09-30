import grpc

from rx.client.configuration import config_base


def get_channel(addr: str) -> grpc.Channel:
  return (
    grpc.insecure_channel(addr) if config_base.is_local() else
    grpc.secure_channel(addr, credentials=grpc.ssl_channel_credentials()))

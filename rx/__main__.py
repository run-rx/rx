"""Rx usage

Configure this directory to be able to run on a remote host:

    rx init

You only have to run this once per directory, similar to `git init`.

To run a command on a configured remote host:

    rx CMD

"""
from rx.client.commands import exec

exec.run()

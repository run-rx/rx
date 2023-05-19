# rx

[rx](https://www.run-rx.com) is a command-line tool to help make remote
execution easy.

When you run rx it creates a private hosted environment in the cloud where all
of your source code is automatically synced and any packages you need are
installed. It automatically syncs output back to your machine and syncs local
changes to your cloud instance.

Right now rx is free to use, please give it a try and [let us know](mailto:eng@run-rx.com) what you think!

## Installation

Install via pip:

    pip install run-rx

rx also requires rsync to run, make sure you have it installed:

    which rsync

If not, check out [its website](https://rsync.samba.org/download.html) or your
favorite package manager to install.

## Usage

In the directory containing your project (often your git root), run:

    rx init

This will prompt you to log in (or create an account) and allocate a machine
in the cloud for you to use. Then it will copy your project from your local
machine to the cloud instance and install any packages that your project needs.

It may take several minutes to allocate a machine, copy your source code, and install packages (depending on your project).

Once rx finishes initializing, you can run any command on your remote worker
by prefixing it with "rx":

    rx python my-script.py
    rx ps ax
    rx 'echo $PATH > my-path.txt'

Check out the [getting-started](https://github.com/run-rx/getting-started) repository for more examples.

## Feedback

Feel free to [file an issue](https://github.com/run-rx/rx/issues) if you have
any questions or problems!

## Testing

To run tests, use:

```
pip install -r test_requirements.txt
PYTHONPATH=. pytest
```

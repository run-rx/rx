# rx

Remote execution made easy.

## Installation

[Download](https://github.com/run-rx/rx/releases/latest) the latest release.
Decompress it and move the `rx` binary onto your path, e.g.,

    tar zxvf rx-0.0.1-nix.tar.gz
    mv rx-0.0.1/rx /usr/local/bin/rx

## Use

In you project's main directory, run:

```
rx init
```

You only have to do this once per project (similar to `git init`).

To execute commands on a remote machine, prefix them with `rx`:

```
rx python foo.py
rx ls
rx ./scripts/my_script.sh
```

Check out the [getting-started](https://github.com/run-rx/getting-started) repository for more examples.

## Feedback

Please file an [issue](https://github.com/run-rx/rx/issues).

## Running from source

If possible, use the self-contained binaries that are provided for Linux, OS X
(Intel), and OS X (Apple silicon). These binaries are pretty fragile, though,
and if you're on an old or strange system, they will probably fail.

If you cannot use the pre-built binaries, the source prerequisites are:

* Python 3.11.2+
* Rsync 3.2.7 ([Install instructions](https://github.com/WayneD/rsync/blob/master/INSTALL.md))
* Project dependencies (`pip install -r requirements.txt`)

### Running directly

`rx`'s entry point is _rx/client/commands/exec.py_. You can
run this directly, so instead of `rx <command>` it's `python -m rx.client.commands.exec --rsync_path=/path/to/rsync-3.2.7 <command>`.

For example, to run `rx init`, use:

    python -m rx.client.commands.exec --rsync_path=/path/to/rsync-3.2.7 init

### Building an executable

To create the self-contained binary for `rx`, install all of the prereqs and
run:

    pyinstaller rx/client/commands/exec.py \
        --add-binary /path/to/rsync:bin \
        --add-data install:install \
        --paths=. \
        --name rx \
        --onefile

This creates `dist/rx`, which can then be copied to your PATH and used normally.

## Testing

To run tests, use:

```
PYTHONPATH=. pytest
```

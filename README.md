# rx

Remote execution made easy.

## Installation

Install the latest release from pip:

    pip install run-rx

rx uses rsync for downloads, so make sure rsync is installed on your
system:

    which rsync

If it isn't, install it with your favorite package manager:

    brew install rsync
    yum install rsync
    apt-get install rsync
    # ...you get the idea

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
rx 'echo $PATH > my-path'
```

Check out the [getting-started](https://github.com/run-rx/getting-started) repository for more examples.

## Feedback

Please file an [issue](https://github.com/run-rx/rx/issues).

## Testing

To run tests, use:

```
pip install -r test_requirements.txt
PYTHONPATH=. pytest
```

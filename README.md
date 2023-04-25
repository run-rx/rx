# rx

Remote execution made easy.

## Installation

[Download](https://github.com/run-rx/rx/downloads) the latest zip file. Unzip it and move the `rx` binary onto your path, e.g., `mv rx /usr/local/bin/rx`.

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

## Testing

To run tests, use:

```
PYTHONPATH=. pytest
```

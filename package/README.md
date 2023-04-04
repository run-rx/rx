# rx

Thanks for downloading rx!

## Installation

To install, add the rx binary to your path, e.g.,

```
sudo cp rx /usr/local/bin
```

## Setup

In you project's main directory, run:

```
rx init
```

You only have to do this once per project (similar to `git init`). It will
open a browser to authenticate you. If you are a new user, you'll be asked to
choose a username.

This will then set up a mirrored environment for you in the cloud, which may
take a few minutes.

## Use

To execute commands on a remote machine, prefix them with `rx`:

```
rx python foo.py
rx ls
rx ./scripts/my_script.sh
```

For more info, see the
[getting-started](https://www.github.com/run-rx/getting-started) repo for a
guided tutorial on using `rx`.

## Feedback

We'd love to hear from you! Please file an
[issue](https://www.github.com/run-rx/rx/issues) on GitHub.

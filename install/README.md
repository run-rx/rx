# Welcome to rx!

This is your config directory. Feel free to replace this file with whatever
you find helpful.

## Remote machines

By default, rx creates two possible remote configs (both Python-based):

* `.rx/remotes/python-cpu`
* `.rx/remotes/python-gpu`

`rx init` defaults to the configuration `.rx/remotes/default` is symlinked to.
You can also specify which config you want with the `--remote` flag:

```
rx init --remote=python-gpu
```

You can change remotes anytime by rerunning rx init with the desired flag or
`default` file.

Feel free to add any other configs you'd like.

[rx](https://www.run-rx.com) is a command-line tool to make remote execution
easy. It integrates with whatever tools you're currently using and gives you a
long-running VM in the cloud that is kept in sync with your local machine.

## Usage

In the directory containing your project (often your git root), run:

    rx init

This will prompt you to log in (or create an account) and allocate a machine
in the cloud for you to use. Then it will copy your project from your local
machine to the cloud instance and install any packages that your project needs.

It may take several minutes to allocate a machine, copy your source code, and
install packages (depending on your project).

Once rx finishes initializing, you can run any command on your remote worker
by prefixing it with "rx":

    rx python my-script.py
    rx ps ax
    rx 'echo $PATH > my-path.txt'

Check out the [getting-started](https://www.run-rx.com/getting-started/)
section for more examples.

## What rx does

When you run rx it takes care of a bunch of cloud setup tasks on your behalf:

* It creates a private hosted environment for your project in the cloud.
* It copies your source code into that environment.
* It installs any dependencies your project needs.

Then, every time you run a command, it automatically syncs local changes to
your cloud instance and syncs outputs back to your local machine. rx hosts
your environment on our own cloud instances, so you never have to worry about
setup or teardown.

Check out the [getting started](https://www.run-rx.com/getting-started) guide
to start using rx in less than five minutes.

*Note: the `rx` binary is a thin client and does not run commands on your local
machine: it sends them to your cloud instance and runs them there.*

We'd love to hear what you think of rx and how you're using it! Please let us
know by emailing eng@run-rx.com or filing an issue on
[GitHub](https://github.com/run-rx/rx/issues)!

## Feedback

Feel free to [file an issue](https://github.com/run-rx/rx/issues) if you have
any questions or problems.

## Running tests

Run tests with:

```
pip install -r requirements_dev.txt
python run_tests.py
```

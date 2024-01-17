from rx.client.commands import command

class AclsCommand(command.Command):
  """Sets the ACLs for this workspace.

  TODO: support add, remove.
  """

  def run(self) -> int:
    return 0

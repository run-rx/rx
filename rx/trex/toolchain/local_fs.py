import pathlib
import subprocess
import tempfile
from typing import List

from rx.client.configuration import local


def get_manifest(local_cfg: local.LocalConfig) -> List[str]:
  dest = tempfile.mkdtemp()
  cmd = [
      local_cfg.rsync_path,
      '--archive',
      '--compress',
      '--delete',
      '--dry-run',
      '--itemize-changes',
  ]
  # Only add the rxignore option if the file exists.
  rxignore = local_cfg.cwd / local.IGNORE
  if rxignore.exists():
    cmd.append(f'--exclude-from={rxignore}')
  cmd += [
      f'{local_cfg.cwd}/',
      str(dest)
  ]
  try:
    result = subprocess.run(cmd, check=True, capture_output=True)
  except subprocess.CalledProcessError as e:
    raise ManifestError(e.stderr.decode('utf-8'))
  stdout = result.stdout.decode('utf-8')
  manifest = []
  for ln in stdout.split('\n'):
    delta = ln.split(' ')
    if len(delta) < 2 or delta[1] == './':
      continue
    filename = delta[1]
    manifest.append(filename)
  return manifest


def dry_run(local_cfg: local.LocalConfig):
  manifest = get_manifest(local_cfg)
  print('Uploading:')
  for filename in manifest:
    tab_count = 1 + filename.count('/')
    is_dir = False
    if filename.endswith('/'):
      is_dir = True
      tab_count -= 1
    tabs = '  ' * tab_count
    slash = '/' if is_dir else ''
    pretty_name = f'{pathlib.Path(filename).name}{slash}'
    # TODO: handle file deletion.
    print(f'{tabs}{pretty_name}')


class ManifestError(RuntimeError):
  pass

"""Install dependencies into the project. Requires Python 3.11+ and Node 22+."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    env = os.environ.copy()
    env['PATH'] = str(ROOT/'.tools/node_modules/node/bin') + os.pathsep + str(ROOT/'.tools/node_modules/.bin') + os.pathsep + env['PATH']
    node = shutil.which('node', path=env['PATH'])
    npm = shutil.which('npm', path=env['PATH'])
    if not node or not npm:
        raise SystemExit('Install Node.js 22+ and npm, then run setup again.')
    version = subprocess.check_output([node, '--version'], env=env, text=True)
    if int(version.lstrip('v').split('.')[0]) < 22:
        raise SystemExit('Node.js 22 or newer is required.')
    target = ROOT/'.venv-local'
    venv.EnvBuilder(with_pip=True, system_site_packages=False).create(target)
    python = target / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT/'apps/api/requirements.txt')], check=True)
    subprocess.run([npm, 'ci' if (ROOT/'apps/web/package-lock.json').exists() else 'install'], cwd=ROOT/'apps/web', env=env, check=True)
    print('Ready. Run: python scripts/dev.py')

if __name__ == '__main__':
    main()

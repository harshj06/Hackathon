"""Run both application processes locally. Ctrl+C stops both children."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    env = os.environ.copy()
    local_node = ROOT / '.tools/node_modules/node/bin'
    env['PATH'] = str(local_node) + os.pathsep + env['PATH']
    node = shutil.which('node', path=env['PATH'])
    python = ROOT / '.venv-local' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    next_cli = ROOT / 'apps/web/node_modules/next/dist/bin/next'
    if not node or not python.exists() or not next_cli.exists():
        print('Run python scripts/setup.py first.', file=sys.stderr)
        return 1
    (ROOT / 'data').mkdir(exist_ok=True)
    env.setdefault('DATABASE_URL', 'sqlite:///' + str(ROOT / 'data/cognify-next.db'))
    env.setdefault('APP_ORIGIN', 'http://localhost:3000')
    env.setdefault('API_INTERNAL_URL', 'http://127.0.0.1:8000')
    processes = []
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        processes.append(subprocess.Popen([str(python), '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'], cwd=ROOT/'apps/api', env=env))
        processes.append(subprocess.Popen([node, str(next_cli), 'dev', '--hostname', '127.0.0.1'], cwd=ROOT/'apps/web', env=env))
        print('Cognify: http://localhost:3000 — Ctrl+C stops both services.', flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(.5)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

if __name__ == '__main__':
    raise SystemExit(main())

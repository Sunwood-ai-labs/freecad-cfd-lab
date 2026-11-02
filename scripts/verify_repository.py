"""Validate public documentation, payload, and saved numerical claims."""
from pathlib import Path
import ast
import json
import re
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
files = [p for p in ROOT.rglob('*') if p.is_file() and not any(
    s in {'.git', 'downloads', '__pycache__', '.venv', 'replay', 'logs'} for s in p.relative_to(ROOT).parts
)]
links = 0
for path in files:
    if path.suffix == '.json':
        json.loads(path.read_text(encoding='utf-8-sig'))
    elif path.suffix in {'.py', '.FCMacro'}:
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    elif path.suffix == '.svg':
        ET.parse(path)
    if path.suffix == '.md':
        body = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.S)
        urls = re.findall(r'\]\(([^)]+)\)', body) + re.findall(r'(?:src|href)="([^"]+)"', body)
        for url in urls:
            if urlsplit(url).scheme or url.startswith('#'):
                continue
            target = path.parent / unquote(url.split('#')[0])
            assert target.exists(), f'Broken local link in {path}: {url}'
            links += 1
    assert path.stat().st_size < 10 * 1024**2, f'Unexpected large Git payload: {path}'

base = ROOT / 'experiments/family-house-airflow'
audit = json.loads((base / 'mesh-geometry-audit.json').read_text(encoding='utf-8'))
assert len(audit['point_checks']) == 69 and all(p['pass'] for p in audit['point_checks'])
solver = json.loads((base / 'solver-validation.json').read_text(encoding='utf-8'))
assert solver['status'] == 'pass'
summary = json.loads((base / 'animation-summary.json').read_text(encoding='utf-8'))
assert summary['frames'] == 480 and summary['duration_s'] == 20
assert summary['source_U_sha256'] == 'ffef09c52a6992f0e2d767942e14c99c1aa60471b26575b3dc8d23337beedc25'
print(json.dumps({'status': 'pass', 'files_checked': len(files), 'local_markdown_links': links}))

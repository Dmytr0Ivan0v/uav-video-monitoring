"""Output files: documents -> JSON / YAML text with stable bytes, sha256 of files."""

import hashlib
import json
from pathlib import Path

import yaml


def write_json(path: Path, doc, compact: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # compact for replay data the browser loads; indented for small files people read
    text = json.dumps(doc, ensure_ascii=False, separators=(',', ':')) if compact else \
        json.dumps(doc, ensure_ascii=False, indent=2)
    with path.open('w', encoding='utf-8', newline='\n') as f:
        f.write(text + '\n')


def write_yaml(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as f:
        yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

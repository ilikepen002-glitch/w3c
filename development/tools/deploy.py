"""Deploy authored Lua into an existing native map and verify hashes."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
header_path = PROJECT / 'header.project'
if not header_path.is_file():
    raise SystemExit('Cannot deploy: create the new native Y3 project first (header.project is missing).')
header = json.loads(header_path.read_text(encoding='utf-8-sig'))
map_name = header['entry_map']['name']
if not isinstance(map_name, str) or not map_name or map_name in ('.', '..') or any(c in map_name for c in ('/', chr(92), ':')):
    raise SystemExit('Cannot deploy: invalid entry map name.')
MAP = PROJECT / 'maps' / map_name
SCRIPT = MAP / 'script'
if not (MAP / 'header.map').is_file() or not (SCRIPT / 'y3/init.lua').is_file():
    raise SystemExit('Cannot deploy: native map or official Lua library is missing.')
sources = sorted((ROOT / 'src').rglob('*.lua'))
if not sources:
    raise SystemExit('Cannot deploy: no authored Lua sources.')
for source in sources:
    relative = source.relative_to(ROOT / 'src')
    if relative.parts[0].lower() == 'y3':
        raise SystemExit('Cannot deploy: authored sources must not overwrite the official y3 library.')
    if not (SCRIPT / relative).resolve().is_relative_to(SCRIPT.resolve()):
        raise SystemExit(f'Cannot deploy outside the script directory: {relative}')
manifest = {}
for source in sources:
    relative = source.relative_to(ROOT / 'src')
    target = SCRIPT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        shutil.copy2(source, target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f'Deploy mismatch: {relative}')
    manifest[relative.as_posix()] = digest
(ROOT / 'output').mkdir(exist_ok=True)
(ROOT / 'output/deploy-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + chr(10), encoding='utf-8')
print(f'DEPLOYED and hash-verified {len(manifest)} Lua files; runtime validation is separate.')

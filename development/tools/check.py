"""Check authored Lua syntax and optionally run a named project test."""
from pathlib import Path
import argparse
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('target', nargs='?', help='Test name under development/tests, without .lua')
args = parser.parse_args()
lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute("package.path = ... .. '/src/?.lua;' .. ... .. '/src/?/init.lua;' .. package.path", ROOT.as_posix(), ROOT.as_posix())
syntax = lua.eval("function(code, name) local f,e=load(code,name); if not f then error(e) end end")
sources = sorted((ROOT / 'src').rglob('*.lua'))
for path in sources:
    syntax(path.read_text(encoding='utf-8-sig'), str(path.relative_to(ROOT)))
print(f'PASS Lua 5.4 syntax: {len(sources)} files' if sources else 'SKIP: no authored Lua sources; no gameplay validation performed.', flush=True)
if args.target:
    if not args.target.replace('_', '').replace('-', '').isalnum():
        parser.error('Test name must contain only letters, digits, underscores or hyphens')
    test = ROOT / 'tests' / (args.target + '.lua')
    if not test.is_file():
        parser.error(f'Test does not exist: {test}')
    lua.execute(test.read_text(encoding='utf-8-sig'))
    print(f'PASS test: {args.target}', flush=True)

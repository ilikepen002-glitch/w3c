"""Run Lua 5.4 syntax, gameplay transactions and complete-campaign simulations."""
from pathlib import Path
import sys
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute("package.path = ... .. '/src/?.lua;' .. ... .. '/src/?/init.lua;' .. package.path", ROOT.as_posix(), ROOT.as_posix())
syntax = lua.eval("function(code, name) local f,e=load(code,name); if not f then error(e) end; return true end")
for path in sorted((ROOT / 'src').rglob('*.lua')):
    syntax(path.read_text(encoding='utf-8'), str(path.relative_to(ROOT)))
print('PASS Lua 5.4 syntax', flush=True)
target = sys.argv[1] if len(sys.argv) > 1 else 'rules'
lua.execute((ROOT / 'tests' / (target + '.lua')).read_text(encoding='utf-8'))

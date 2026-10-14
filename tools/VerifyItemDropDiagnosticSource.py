"""Read-only source guard for the opt-in item-drop observer.

This does not emulate Warcraft events, timers, cursor projection or relocation.
Run Wurst checks/build and use a retail-client screenshot for those boundaries.
"""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '2847c3f'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def verify():
    source = (ROOT / 'wurst/items/TDItemDropDiagnostic.wurst').read_text()
    code = re.sub(r'//[^\n]*', '', source)
    forbidden = ('SetItemPosition', 'UnitRemoveItem', 'UnitAddItem', 'RemoveItem',
                 'CreateItem', 'SetTerrainPathable', 'IssuePointOrder',
                 'IssueTargetOrder', 'GetLocalPlayer', 'GetOrderPoint',
                 'GetOrderTarget', 'GetManipulatedItem', 'EnumItems',
                 'GroupEnumUnits', 'SetPlayerState', 'SetUnitState')
    for name in forbidden:
        require(name not in code, 'Observer must not call ' + name)
    require('0x48' not in source and 'WPM=' not in source, 'Runtime observer must not invent static WPM bytes')
    require('坑道掩码=路' in source and '坑道掩码=非源区' in source, 'Report only actual source-mask membership')
    require('boolean array tdDropTraceEnabled' in code, 'Default false per-player gate missing')
    require('"-dropdiag", true' in code, 'Chat command must match exactly')
    require(code.count('CreateTimer()') == 2, 'Only the two bounded observation timers may be created')
    drop = code.split('public function tdItemDropDiagnosticDropped(', 1)[1].split('\npublic function', 1)[0]
    require(drop.index('not tdDropTraceEnabled[lane]') < drop.index('CreateTimer()'), 'Off path may not create timers')
    require('TimerStart(tdDropTraceNextTimer[lane], 0.0, false' in drop, 'Final observation must be deferred and one-shot')
    require('TimerStart(tdDropTraceExpiryTimer[lane], TD_ITEM_DROP_TRACE_SECONDS, false' in drop, 'Watch must expire')
    require('tdItemDropDiagnosticPickedUp(itm)' in drop, 'Carrier changes must invalidate prior watch')
    require('tdDropTraceMoves[lane] >= 32' in code, 'Bound diagnostic output')
    require('目标未知' in source and '事件时(非最终)' in source, 'Do not manufacture an intent or final event position')
    for member in ('tdDropTraceNextTimer', 'tdDropTraceExpiryTimer'):
        require(f'DestroyTimer({member}[lane])' in code and f'{member}[lane] = null' in code, 'Timer cleanup missing')
    require('function tdDropTraceLeave()' in code, 'Leave cleanup missing')
    require('tdIsGameOver()' in code and 'IsItemOwned(itm)' in code and 'GetItemTypeId(itm) != 0' in code,
            'Callback must reject ended games, picked-up or invalid items')
    # Remove only the newly added observer imports/calls and prove the pre-existing
    # gameplay code is otherwise byte-for-byte identical to the exact base commit.
    for name in ('wurst/items/TDInventoryRuntime.wurst', 'wurst/items/TDItemPlacement.wurst',
                 'wurst/towers/TDTowerRuntime.wurst'):
        text = (ROOT / name).read_text()
        stripped = ''.join(line for line in text.splitlines(keepends=True)
                           if not re.match(r'\s*(?:import TDItemDropDiagnostic|tdItemDropDiagnostic\w*\(|tdSetupItemDropDiagnostic\()', line))
        original = subprocess.check_output(['git', 'show', f'{BASELINE}:{name}'], cwd=ROOT, text=True)
        require(stripped == original, 'Existing gameplay changed beyond observation hooks: ' + name)
    original_sort = subprocess.check_output(['git', 'show', f'{BASELINE}:wurst/items/TDGroundItemRuntime.wurst'], cwd=ROOT)
    require((ROOT / 'wurst/items/TDGroundItemRuntime.wurst').read_bytes() == original_sort, 'Periodic sorting changed')
    print('PASS: opt-in bounded source observer; gameplay source unchanged after removing observation hooks')


if __name__ == '__main__':
    verify()

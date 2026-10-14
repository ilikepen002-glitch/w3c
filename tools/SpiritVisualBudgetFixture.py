"""Native-clock fixtures which reserve the packed production visual budgets.

Tokens intentionally own no native art. Callers return each token through its
matching production release API; no production count/list is overwritten here.
"""
from VerifyEquipmentAbilityArtifact import require


def classified(runtime):
    return 'tdCombatVisualAcquireCore' in runtime.functions


def reserve(runtime, count, core=False, advance=False):
    require(count >= 0, 'Negative visual fixture reservation')
    acquire = 'tdCombatVisualAcquireCore' if core else 'tdCombatVisualAcquireCast'
    release = 'tdCombatVisualReleaseCore' if core else 'tdCombatVisualReleaseCast'
    held = []
    for _ in range(count):
        if not runtime.invoke(acquire):
            require(advance, 'Actual visual fixture reservation failed '+str((acquire, count, len(held))))
            runtime.now = float(int(runtime.now)+1)
            require(runtime.invoke(acquire), 'Visual fixture remains blocked after its creation-window reset')
        held.append(release)
    return held


def release(runtime, held):
    for method in held:
        runtime.invoke(method)


def spend(runtime, count, core=False):
    """Exhaust creation tickets without keeping a live reservation."""
    for _ in range(count):
        held = reserve(runtime, 1, core=core)
        release(runtime, held)


def saturate(runtime, total):
    """Fill a total live quota with its legal classified composition."""
    require(0 <= total <= 128, 'Shared visual fixture requested an invalid live count')
    if not classified(runtime):
        return reserve(runtime, total, advance=True)
    decoration = min(total, 88)
    return reserve(runtime, decoration, advance=True)+reserve(runtime, total-decoration, core=True, advance=True)


def core_count(runtime):
    # Diagnostic getters are removed by the final map's dead-code elimination.
    # This is the actual admission owner's production field, not a substitute.
    return runtime.globals['TDCombatVisualRuntime_coreVisualCount']


def buff_count(runtime):
    # The former independent buff counter is now dead code: count the actual
    # source-owned native handles, and check the counter if a packed map keeps it.
    count = sum(bool(runtime.globals['TDVisualSource_petBuff'][owner])
                for owner in runtime.lists[runtime.globals['TDCombatVisualRuntime_sources']])
    if 'TDCombatVisualRuntime_petBuffVisualCount' in runtime.globals:
        require(runtime.globals['TDCombatVisualRuntime_petBuffVisualCount'] == count,
                'Packed buff counter differs from actual source-owned native handles')
    return count

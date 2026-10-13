#!/usr/bin/env python3
"""Read-only, fail-closed four-pure-Boss source and final-MPQ gate.

The supplied baseline must be an immutable formal release (b7, then the entire
published spirit-management release), never an unpublished working tree. Run:
  python tools/VerifyPureBossArtifact.py candidate.w3x --baseline-map formal.w3x \
      --source candidate/wurst --baseline-source formal/wurst \
      --approved-source-owner TDGame.wurst ...
--source-only performs only the source contract; it never claims an MPQ PASS.
This tool does not compile, generate resources, edit a map, or launch Warcraft.
Unknown generated aliases/dispatch ranges fail closed, rather than being erased.
Native stubs expose engine boundaries; they never implement a Boss rule/reward.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import replace
import difflib
import hashlib
import itertools
import json
from pathlib import Path
import re
import struct
import subprocess

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifySemanticIconArtifact import parse_objects, decode_blp
from VerifyGlobalRankingsArtifact import members, normalize_info, OBJECTS
from VerifyDamageRankingJass import functions
from VerifyBuilderControlDelta import allocations, ASSIGN, TYPE_TEST, TOKEN, TEMP
from VerifyInheritedJassAliases import inherited_script_view
from VerifyBossSpellResistanceArtifact import BossJassRuntime, close, verify_engine_and_accounting
from VerifyTowerUpgradeArtifact import rawcode

ROOT = Path(__file__).resolve().parents[1]
BOSS_WAVES = (8, 16, 24, 32)
BOSS_HP = (3200, 6800, 19000, 36000)
BOSS_ARMOR = (2, 10, 9, 8)
BOSS_GOLD = (55, 90, 144, 200)
BOSS_NAMES = ('裂风猎王', '黑曜棺卫', '蚀月织咒者', '无冕深渊君王')
ICON_STEMS = ('Riftwind', 'Obsidian', 'Eclipse', 'Abyss')
# Independent approved bytes, not accepted from a candidate-controlled manifest.
ICON_SHA = {
    'Riftwind': ('b8f0db393bc2463e83faf1a1a264011f4cb0bad1c0f647440e0c308e08978189', 'bd7d893ab96ff8f2ad8212e429e5d319de4d7d95c2cd395a9491b21333441efc'),
    'Obsidian': ('1b41be2e35ca40c90c53dbf48f5308249054eef6754d949394aeca97c7b17d17', '234c800154041335a851bede327c052977a3c5344056aa32e496eee09b09aee8'),
    'Eclipse': ('72458f5c99f72b44a55e26b409c8f172d342cc7b8b6a90a2a6b1f554472ed864', 'ed2788545294aadbc3293b1c35a7762518f030d26c63735e9cc72ba05b3b4dbe'),
    'Abyss': ('d739814a45763415b248881a5cc7235d50c270492e95d332f8448761e85a1588', 'd1854557c16920c25ddd4a26409fa02286477350486b513f005be8a1b1129452'),
}
NEW_OWNERS = frozenset(('TDWaveFlowState.wurst', 'TDBossTransitionHook.wurst',
    'enemies/TDBossDarkTideRuntime.wurst', 'items/TDBossRewardRules.wurst',
    'items/TDBossLootPlan.wurst', 'items/TDBossRewardRuntime.wurst'))
CHANGED_OWNERS = NEW_OWNERS | frozenset(('TDGame.wurst', 'TDHud.wurst', 'TDInit.wurst',
    'TDSpawn.wurst', 'TDState.wurst', 'TDWaves.wurst', 'enemies/TDEnemyMechanicData.wurst',
    'enemies/TDEnemyMechanicObjectGen.wurst', 'enemies/TDEnemyMechanicRuntime.wurst',
    'enemies/TDEnemyMechanicState.wurst', 'pets/TDPetRules.wurst',
    'pets/TDPetRuntime.wurst', 'pets/TDPetState.wurst', 'pets/TDPetWild.wurst',
    'towers/TDTowerEvolutionState.wurst', 'towers/TDTowerRuntime.wurst'))
# Only these declarations may change in otherwise preserved shared packages.
CHANGED_DECLS = {
    'TDGame.wurst': {'tdHandleGameResolved', 'tdClearLaneEnemiesEnum', 'tdHandleEnemyLeak',
        'tdStartLeakWatcher', 'tdStartEnemyDeathWatcher', 'tdClaimEnemyKill', 'tdHandleEnemyDeath',
        'tdScheduleForcedNextWave', 'tdTryScheduleNextWave', 'tdStartGlobalWave',
        'tdStartWaveSchedule', 'tdHandleWaveFinished'},
    'TDSpawn.wurst': {'tdOrderEnemyAlongLane', 'tdCreateEnemy', 'tdAdvanceEnemyWaypoint',
        'tdLaneEnemyCheckEnum', 'tdWaitForLaneToClear', 'tdSpawnWave', 'tdStartLaneWaypointWatcher'},
    'TDHud.wurst': {'tdRefreshStatusBoard'},
    'enemies/TDEnemyMechanicRuntime.wurst': {'TDEnemyMechanicRecord', 'tdEnemyMechanicRecordValid',
        'tdEnemyMechanicRetireRecord', 'tdEnemyMechanicRegister', 'tdEnemyMechanicOnWaypoint',
        'tdEnemyMechanicsTick', 'tdEnemyMechanicsShutdown', 'tdEnemyMechanicBaseSpeed'},
    'enemies/TDEnemyMechanicState.wurst': {'TDEnemyMechanicState'},
    'enemies/TDEnemyMechanicData.wurst': {'tdEnemySprintEnabled', 'tdEnemyMechanicTracked',
        'tdEnemyMechanicMaxSpeed', 'tdEnemyMechanicHint'},
    'enemies/TDEnemyMechanicObjectGen.wurst': {'tdGenerateEnemyMechanicObjects'},
}
REMOVED_DECLS = {'enemies/TDEnemyMechanicState.wurst': {'TDEnemyGuardLink'},
    'enemies/TDEnemyMechanicRuntime.wurst': {'tdEnemyGuardLinkIndex', 'tdEnemyGuardLinkFor',
        'tdEnemyMechanicSyncArmor', 'tdEnemyMechanicSyncLink'},
    'enemies/TDEnemyMechanicData.wurst': {'tdEnemyGuardArmorEnabled'}}


NEW_DECLS = {
    'TDInit.wurst': {'tdHandleLanePlayerLeaveEvent', 'tdSetupLanePlayerLeaveWatcher'},
    'TDGame.wurst': {'tdClaimEnemyKill', 'tdBeginBossIntermission', 'tdPrepareBossRound', 'tdSettleBossFailure', 'tdCloseDefeatedLane', 'tdResumeBossTransition', 'tdHandleLanePlayerLeft', 'tdContinuingLanesEmpty', 'tdBossPreparationReady', 'tdBossCanSettle', 'tdStartPreparedBoss', 'tdShutdownGameFlow', 'tdRegisterBossTransitionHook', 'tdScheduleWaveAfterDelay', 'tdWatchBossRound'},
    'TDSpawn.wurst': {'tdForgetEnemyMatch', 'tdEnemyBelongsToCurrentMatch', 'tdMarkEnemyKilled', 'tdEnemyDeathWasSettled'},
    'TDHud.wurst': {'tdHudSetBossIcon', 'tdHudBossMechanicText'},
    'enemies/TDEnemyMechanicRuntime.wurst': {'tdEnemyMechanicIsRegistered'},
    'enemies/TDEnemyMechanicData.wurst': {'tdEnemyBossSpellResistanceEnabled', 'tdBossIconPath', 'tdIsPureBossWave'},
    'TDWaveFlowState.wurst': {'tdFlowClaimBossResult', 'tdResetWaveFlowState', 'tdFlowCallTransitionReady', 'tdFlowStartBoss', 'tdFlowEnterIntermission', 'tdFlowBossExpired', 'tdFlowTransitionIsHeld', 'tdFlowEnterNormal', 'tdFlowBossRewardWasClaimed', 'tdFlowClaimBossLoot', 'tdFlowPendingBossWave', 'tdFlowEndSpawn', 'tdFlowActivateBoss', 'tdFlowIsPreparing', 'tdFlowSchedule', 'tdFlowClaimBossReward', 'tdFlowEpoch', 'tdFlowPhaseForTest', 'tdFlowHoldTransition', 'tdFlowHasTransitionHook', 'tdFlowTransitionBlocksAdvance', 'tdFlowHeldTransitionToken', 'tdFlowIsIntermission', 'tdFlowRegisterTransitionHook', 'tdFlowIsBossActive', 'tdFlowBossResult', 'tdFlowSpawnCallbackValid', 'tdFlowCancelLane', 'tdFlowBeginSpawn', 'tdFlowBossSecondsRemaining', 'tdFlowReleaseTransition', 'tdFlowPrepareBoss', 'tdFlowLaneHasPendingSpawn', 'tdFlowClaimBossBallCompensation'},
    'TDBossTransitionHook.wurst': {'TDBossTransitionHook'},
    'enemies/TDBossDarkTideRuntime.wurst': {'tdDarkTideShutdown', 'tdDarkTideTowerEligible', 'tdDarkTideApply', 'tdDarkTideForgetTower', 'tdDarkTideForgetBoss', 'tdDarkTideTick', 'TDBossDarkTideRecord', 'tdDarkTideClearLane'},
    'items/TDBossLootPlan.wurst': {'TDBossLootPlan'},
    'items/TDBossRewardRules.wurst': {'tdBossBallDropSucceeds', 'tdBossNormalDropAttempts', 'tdBossKillCompensation', 'tdBossBonusDropSucceeds', 'tdBossBallDropAttempts'},
    'items/TDBossRewardRuntime.wurst': {'tdHandlePureBossLoot', 'tdCreateBossLootItem'},
}
# Exact source checkpoint templates. Updating these requires reviewing the
# new source change; candidate-supplied manifests cannot widen these contracts.
SOURCE_OWNER_TEMPLATES = {'TDBossTransitionHook.wurst': 'bf715f96cbd066eb39782c5c9f53900dbdb85fe63b11dd068c3f29e6c7adc946',
 'TDWaveFlowState.wurst': '87da2036f00be5001a241215621b9cc0bd4bd2228082df05bd184c7073b746e8',
 'enemies/TDBossDarkTideRuntime.wurst': '0209ff18248c94c8141ac589703964365453f7cf8e2fd431594485fee57be220',
 'items/TDBossLootPlan.wurst': '22cfe56d402fbb6d7fc3bcd86af1d7e09db0551b0e3146a473d2f7e0ad2b12a5',
 'items/TDBossRewardRules.wurst': 'c3308ee6af7afbd3ffdcf808c821f3254bb305b64d6303b444b7b264fb95fd18',
 'items/TDBossRewardRuntime.wurst': 'c9ab357849f99c0a6051b3a5c440509d76032029f6487b16a2de662ae0f8902d'}
SOURCE_DECLARATION_TEMPLATES = {'TDInit.wurst::tdHandleLanePlayerLeaveEvent': '73666930ec95c216e0126787c70128ea1b585fc3797f4ecdb412a18d0045818c',
 'TDInit.wurst::tdSetupLanePlayerLeaveWatcher': 'e27b0c646f3965adbfd39ff155308e93681d852e8c7f94b34978d29042d2ec09',
 'TDGame.wurst::tdBeginBossIntermission': 'a69ccc5efa660c735452f7fc51ae3e9703aae691a049034df4e5a0020fcfed1f',
 'TDGame.wurst::tdBossCanSettle': '15a216e87a4a73eeebc211a355bb3163aaddc1ab998ed4df09b2f33236a69661',
 'TDGame.wurst::tdBossPreparationReady': '0bc14260e7bf0e50df4c1ea3b3f59ab4cd3c7571fd3c705b0de3632c6009c9f7',
 'TDGame.wurst::tdClaimEnemyKill': '1ba2f60b90bea334860246f2350bc610357d2d87439172477449c243a711356c',
 'TDGame.wurst::tdClearLaneEnemiesEnum': '1f718d13ff7fdab95d62fe4533fd350c4b40c8cc7145c54486182b67f663e671',
 'TDGame.wurst::tdCloseDefeatedLane': '96b2756c3f552eb966bd326d9479bb99d64710c3d180107062f30e49b087d6e1',
 'TDGame.wurst::tdContinuingLanesEmpty': '71a9c959a9bbdb56a8a212eaf7e49cb893487d1c0328b4b538fef1c6166de24f',
 'TDGame.wurst::tdHandleEnemyDeath': '4c7f39e381d410209a85807e209c8b813b774603f16bc10ff6e0bb7c550c633a',
 'TDGame.wurst::tdHandleEnemyLeak': '05ee148f423e5ccf73b2decea04c1ecb5c28f5c1470e40760a7dd7a56c5f46a4',
 'TDGame.wurst::tdHandleGameResolved': '31ac55c1e07d0a802b4f203102db73b19dd755ed98fd7e700af835628e19bf80',
 'TDGame.wurst::tdHandleLanePlayerLeft': '07116f7532eab095542cb700e881e754f674dc9f666f092b9c867ca5a20b7a41',
 'TDGame.wurst::tdHandleWaveFinished': 'a64821087057e2e1d538768406aad863a0339e9b7c2cf3600b1bc942842c9acb',
 'TDGame.wurst::tdPrepareBossRound': '4651eb8509cdb98c50ee887e07725738e42cbe4ed718b2018da86d8a594577e0',
 'TDGame.wurst::tdRegisterBossTransitionHook': '2010e515619b5d327ae7062cf2ccc609ab9ced22b7a36e1947321ffa1d56e6b5',
 'TDGame.wurst::tdResumeBossTransition': 'a761854021577bc08577853df8a0e41de571e4a88a36a20d73dbe22c9116f198',
 'TDGame.wurst::tdScheduleForcedNextWave': 'a325c0fdb7c402753e7bb35dae2abe56bc24c47878c649e51f005481c65691b3',
 'TDGame.wurst::tdScheduleWaveAfterDelay': 'fe162bb252ed6ff3e71241e2d546173910d1c18e62ba9494d63d349784269e70',
 'TDGame.wurst::tdSettleBossFailure': '8017dbd8a61c34b007af404de030184124a0450a8b59bcb5a98f5aac24b72040',
 'TDGame.wurst::tdShutdownGameFlow': 'aac79cc8d7a69bf06d1a34a97c04c0ada43579153bc8d086ea8277314daa90f4',
 'TDGame.wurst::tdStartEnemyDeathWatcher': '1007fc571471b04fb2923c4a7cbf6b2a6bc1aad87b8cf1a8aa5af551117407e8',
 'TDGame.wurst::tdStartGlobalWave': '020fd93afa24d6b1f9b5377ab35daafae4f135d8dbec8c17092b82293ecf66f7',
 'TDGame.wurst::tdStartLeakWatcher': '91c4b4d8e1e8af9abbeff7bc84c97178d8559458aeda2fdf7e97b7157422fda2',
 'TDGame.wurst::tdStartPreparedBoss': 'd3bb4ad827e8e7f2f5e2cad9593263663eae09447f28a30e37858b3a153feb58',
 'TDGame.wurst::tdStartWaveSchedule': 'ff09cc91bb5f303a3828269f9f223ad454dc956ce1c45b80e130c4f02c320d14',
 'TDGame.wurst::tdTryScheduleNextWave': 'aa81535afbdc9dba96acacdfd527cc8c22b22ce102d303fbb9b94829489c82fd',
 'TDGame.wurst::tdWatchBossRound': '3888c733f8d8d4f3547176754841ebb541de48dc361b76485255c7cbd3dc265e',
 'TDHud.wurst::tdHudBossMechanicText': 'f5359ab7fc62405d35e1ed4e5ee3f72e842dad308bc28488db6bf8597d228c2f',
 'TDHud.wurst::tdHudSetBossIcon': 'ddfe0f25544135ab1ac7f713a57b787655165f5b48480e8713d821c0e3d3bcdf',
 'TDHud.wurst::tdRefreshStatusBoard': 'e2a282865e75c16661098ca4e1c2a5b62a9880606a10de91361520c1a341dcfa',
 'TDSpawn.wurst::tdAdvanceEnemyWaypoint': 'b0b1152657270656ef4f609618b25b67a4b818da03c96025f2e556699ef57797',
 'TDSpawn.wurst::tdCreateEnemy': '20e3a565e1e194bd037c2b2290d733d6dcf7b855a804f8a6352112c8b18d0948',
 'TDSpawn.wurst::tdEnemyBelongsToCurrentMatch': 'e9a205a1dc46429b98d4ae01307e51d6980a336cf62c3af379dcae7c04a2797c',
 'TDSpawn.wurst::tdEnemyDeathWasSettled': '4e158cec9bc6275238a5aac2e864c99e2a89e8e0403f4bf5da054dbe059a0f41',
 'TDSpawn.wurst::tdForgetEnemyMatch': '282d8737b51285f97f2571fb4acf0cb38043fa61d43b63a62bc39292cc9f1781',
 'TDSpawn.wurst::tdLaneEnemyCheckEnum': 'd30d6bba56c5b8a938c2cb394ddca7141902c9683b39491b197e796b08ba56bf',
 'TDSpawn.wurst::tdMarkEnemyKilled': '6a6a7ec20d94acbbc14b801844ec0213926dfcaf507932a1c9f9d1bc999d4078',
 'TDSpawn.wurst::tdOrderEnemyAlongLane': 'e83dc98cf152da86f376a512c01e84cb7711a06e088079ba5ce28530b168238b',
 'TDSpawn.wurst::tdSpawnWave': 'cfe34abe94bdb57f76dc0d649922043796c9073527de998f7487028129e94e60',
 'TDSpawn.wurst::tdStartLaneWaypointWatcher': '750f5a933e5177761d3a623f5635b2620c5d6ef7aebde88ec668abe605c6e984',
 'TDSpawn.wurst::tdWaitForLaneToClear': '6c7456e1bdd93b8443690539c59dd928192c9410398f42dcb3bb0c03d6530b5e',
 'enemies/TDEnemyMechanicData.wurst::tdBossIconPath': '3b368b3f4b62f46a62f27d92475799fe87167938c17fdfdeb600a7d3822f2531',
 'enemies/TDEnemyMechanicData.wurst::tdEnemyBossSpellResistanceEnabled': 'dd83f917d93f0200ef7c47ba9b0d55f6e97f89ff7bf56d6ed2cb2a03d47341cf',
 'enemies/TDEnemyMechanicData.wurst::tdEnemyMechanicHint': '45e3d081d61dc8f86b021e755ee3715b5b1e427097b8b018c45a3cbb10991c19',
 'enemies/TDEnemyMechanicData.wurst::tdEnemyMechanicMaxSpeed': '75cb4d1c3a4c30468337dbbe2bc7c39e64f083800a1c14cf27e688e7ea4d6ce1',
 'enemies/TDEnemyMechanicData.wurst::tdEnemyMechanicTracked': '294d0665dab55fd4bc9d5e4557f75fab5926721114c74ca5d44744ad31969908',
 'enemies/TDEnemyMechanicData.wurst::tdEnemySprintEnabled': '9c35c023ef30b47c971e7c8d2f71d4cfbe7af0052202c8288f0733626fc2ce7e',
 'enemies/TDEnemyMechanicData.wurst::tdIsPureBossWave': '523ce341da46763794c79194746688e64a8e2eacae4b0738894a42eda22a4ded',
 'enemies/TDEnemyMechanicObjectGen.wurst::tdGenerateEnemyMechanicObjects': '79840e4a1c81def58b7f8c2bf38b1aa679f0b2924fc817e553ad5c68bd489755',
 'enemies/TDEnemyMechanicRuntime.wurst::TDEnemyMechanicRecord': '9e2366d638ef3e524f8b1074ee26e75f17839c6e00525ad723e2981e9a22cb61',
 'enemies/TDEnemyMechanicRuntime.wurst::tdEnemyMechanicBaseSpeed': '1fd4bba18d511bc88334942a7acc83d45317f733252331d5f6496502396e60bf',
 'enemies/TDEnemyMechanicRuntime.wurst::tdEnemyMechanicIsRegistered': 'ee4274d1c045eb110283d6a77ff37be77acb59b49b979c089f98e31d43f688d9',
 'enemies/TDEnemyMechanicRuntime.wurst::tdEnemyMechanicOnWaypoint': '95f1e507f818d511e2efe47e7afa051dc75d34a3a2ea91ab0d2dd3cd2c094643',
 'enemies/TDEnemyMechanicRuntime.wurst::tdEnemyMechanicRecordValid': 'ee9b394c67165cda0d2195e4d88b5f11210858d204974932f5b8e2fcb2ced42d',
 'enemies/TDEnemyMechanicRuntime.wurst::tdEnemyMechanicRegister': 'af7d7fd90948e9e36a02f81b6799ce7c5b2955231054e8a5ad54188af5d968aa',
 'enemies/TDEnemyMechanicRuntime.wurst::tdEnemyMechanicRetireRecord': '50b99d773bde9022dd6ba4b466547e3b4dd27cc4d12818d006648670c9e1b760',
 'enemies/TDEnemyMechanicRuntime.wurst::tdEnemyMechanicsShutdown': '76f898dddbb1e621b252b11843fd934506330c8e896a1285dea7b4bb655d1287',
 'enemies/TDEnemyMechanicRuntime.wurst::tdEnemyMechanicsTick': '8e2ba88f1509a6b276b5e19299b0a631db1a89b049e76ba7bc619e939d2b9788',
 'enemies/TDEnemyMechanicState.wurst::TDEnemyMechanicState': '68dcab4608bc80e8508dcc43b17e4cc3e4127c8765fad8b5af6d723ebb8a8eac'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_root(path):
    path = Path(path).resolve()
    return path / 'wurst' if (path / 'wurst').is_dir() else path


def source_files(root):
    root = source_root(root)
    return {p.relative_to(root).as_posix(): p.read_text(encoding='utf-8')
            for p in sorted(root.rglob('*.wurst')) if '_tests' not in p.relative_to(root).parts}


def verify_manager_inherited_wiring():
    """Keep the Manager-stage wild freeze while validating the actual combination.

    Current wild changes are authorized only by this whole-source exact Boss
    delta against immutable formal654. The Manager wiring oracle is otherwise
    unchanged and still defaults to its original historical byte freeze.
    """
    import VerifyPetManagerSource as manager
    formal = '654771baa872241cf572b16a0ef884436fe4818c'
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', formal, 'wurst'], cwd=ROOT).decode().splitlines()
    baseline = {p.removeprefix('wurst/'): subprocess.check_output(['git', 'show', formal + ':' + p], cwd=ROOT).decode()
                for p in paths if p.endswith('.wurst') and '/_tests/' not in p}
    proof = verify_source_delta(source_files(ROOT / 'wurst'), baseline, CHANGED_OWNERS)
    manager.verify_wiring(verify_legacy_wild_scope=False)
    return {'source_delta': proof, 'manager_wiring': 'PASS; only historical wild byte-scope delegated to the exact formal654 Boss source proof'}


def declarations(source):
    """Top-level source declarations, including complete class method bodies.

    Comments/whitespace are retained in the residual, so they cannot conceal a
    production edit. Overloads are keyed by complete signature when necessary.
    """
    pattern = re.compile(r'^(?:@compiletime )?(?:public )?(?:function|class|interface) ([\w.]+)[^\n]*\n(?:[\t ][^\n]*\n|\n)*', re.M)
    result = defaultdict(list)
    for match in pattern.finditer(source):
        result[match[1]].append(match[0])
    return dict(result)


def source_function(source, name):
    values = declarations(source).get(name, [])
    require(len(values) == 1, 'Source declaration missing/ambiguous: ' + name)
    return values[0]


def ordered(text, snippets, context):
    cursor = 0
    for snippet in snippets:
        index = text.find(snippet, cursor)
        require(index >= 0, context + ': missing/out-of-order ' + snippet)
        cursor = index + len(snippet)


def exact_replace(text, old, new, count=1):
    require(text.count(old) == count, 'Formal source expected exact occurrence: ' + old[:90])
    return text.replace(old, new)


def expected_partial(path, before, after):
    """Exact intended edits for owners carrying unrelated game/tower/pet logic."""
    expected = before
    if path == 'TDState.wurst':
        expected = exact_replace(expected, 'import TDConfig\n', 'import TDConfig\nimport TDWaveFlowState\n')
        expected = exact_replace(expected, 'public function tdResetState()\n', 'public function tdResetState()\n\ttdResetWaveFlowState()\n')
    elif path == 'TDInit.wurst':
        expected = exact_replace(expected, '首领3。\"', '首领3。首领关每路1名，入场后90秒限时。\"')
        expected = exact_replace(expected, 'public function tdStartGame()\n', 'public function tdStartGame()\n\ttdShutdownGameFlow()\n')
        expected = exact_replace(expected, 'import TDDamageRuntime\n', 'import TDDamageRuntime\nimport RegisterEvents\n')
        expected = exact_replace(expected, 'boolean tdGameplayStartupCompleted = false\n', 'boolean tdGameplayStartupCompleted = false\n// This listener lives for the process, independently of match resets.\nboolean tdLanePlayerLeaveWatcherReady = false\n')
        expected = exact_replace(expected, '\ttdSetupPets()\n', '\ttdSetupPets()\n\ttdSetupLanePlayerLeaveWatcher()\n')
        stripped = after
        for name in ('tdHandleLanePlayerLeaveEvent', 'tdSetupLanePlayerLeaveWatcher'):
            stripped = stripped.replace(source_function(after, name), '', 1)
        require(stripped == expected, 'TDInit.wurst: source changed outside exact approved lifecycle edits')
        return after
    elif path == 'towers/TDTowerEvolutionState.wurst':
        expected = exact_replace(expected, 'TD_EVOLUTION_KILL_REQUIREMENT = 250', 'TD_EVOLUTION_KILL_REQUIREMENT = 220')
    elif path == 'pets/TDPetState.wurst':
        expected = exact_replace(expected, 'import TDState\n', 'import TDState\nimport TDEnemyMechanicData\n')
        old = source_function(expected, 'tdPetClaimWildSpawn')
        new = exact_replace(old, 'wave < 1 or wave > 32\n', 'wave < 1 or wave > 32 or tdIsPureBossWave(wave)\n')
        expected = expected.replace(old, new, 1)
    elif path == 'pets/TDPetRules.wurst':
        expected = exact_replace(expected, 'wave == 13 or wave == 16 or wave == 19', 'wave == 13 or wave == 17 or wave == 19')
    elif path == 'towers/TDTowerRuntime.wurst':
        expected = exact_replace(expected, 'package TDTowerRuntime\n', 'package TDTowerRuntime\nimport TDBossDarkTideRuntime\n')
        funcs = ('tdHandleTowerSellCast', 'tdHandleTowerUpgradeStarted', 'tdRejectTowerConstruction',
                 'tdHandleTowerConstructionCancelled', 'tdHandleTowerDeath')
        for name in funcs:
            old, new = source_function(expected, name), source_function(after, name)
            require(new.count('tdDarkTideForgetTower(tower)') == 1, name + ': cleanup must appear once')
            stripped = re.sub(r'^[ \t]*tdDarkTideForgetTower\(tower\)\n', '', new, flags=re.M)
            require(stripped == old, name + ': unrelated tower implementation changed')
            expected = expected.replace(old, new, 1)
    elif path == 'TDWaves.wurst':
        changes = [('public function tdWaveNormalEnemyCount(int wave) returns int\n', 'public function tdWaveNormalEnemyCount(int wave) returns int\n\tif tdIsPureBossWave(wave)\n\t\treturn 0\n'),
            ('\tif wave == 8 or wave == 16\n\t\treturn 1\n\tif wave == 24 or wave == 32\n\t\treturn 2\n', ''),
            ('tdScaledEnemyStat(1800, tdEnemyHealthMultiplier())', 'tdScaledEnemyStat(3200, tdEnemyHealthMultiplier())'),
            ('tdScaledEnemyStat(4500, tdEnemyHealthMultiplier())', 'tdScaledEnemyStat(6800, tdEnemyHealthMultiplier())'),
            ('tdScaledEnemyStat(9500, tdEnemyHealthMultiplier())', 'tdScaledEnemyStat(19000, tdEnemyHealthMultiplier())'),
            ('tdScaledEnemyStat(18000, tdEnemyHealthMultiplier())', 'tdScaledEnemyStat(36000, tdEnemyHealthMultiplier())'),
            ('\t\treturn 0.82\n', '\t\treturn 1.00\n'),
            ('\tvar text = tdWaveNormalName(wave) + " ×" + tdWaveNormalEnemyCount(wave).toString()', '\tvar text = tdWaveNormalEnemyCount(wave) > 0 ? tdWaveNormalName(wave) + " ×" + tdWaveNormalEnemyCount(wave) : ""'),
            ('\t\ttext += "、" + tdWaveBossName(wave)', '\t\ttext += (text == "" ? "" : "、") + tdWaveBossName(wave)')]
        for old, new in changes:
            expected = exact_replace(expected, old, new)
        expected = exact_replace(expected, 'tdWaveBossName(wave) + " ×" + tdWaveBossEnemyCount(wave).toString()', 'tdWaveBossName(wave) + " ×" + tdWaveBossEnemyCount(wave)')
        for old, new in zip(('早期Boss', '阶段Boss', '后期Boss', '最终Boss'), BOSS_NAMES):
            expected = exact_replace(expected, '"' + old + '"', '"' + new + '"')
        old = source_function(expected, 'tdWaveBossArmor')
        new = old.replace('tdScaledEnemyStat(6,', 'tdScaledEnemyStat(10,').replace('tdScaledEnemyStat(12,', 'tdScaledEnemyStat(8,')
        expected = expected.replace(old, new, 1)
        for wave in BOSS_WAVES:
            line = f'..tdApplyEscaperStats(tdWaveBossName({wave}), tdWaveBossHitPoints({wave}), tdWaveBossArmor({wave}), tdWaveBossSpeed({wave}))\n'
            expected = exact_replace(expected, line, line + f'\t..setSpeedMaximum(tdEnemyMechanicMaxSpeed({wave}, TD_ENEMY_ROLE_BOSS, tdWaveBossSpeed({wave})))\n\t..setIconGameInterface(tdBossIconPath({wave}))\n')
    elif path == 'pets/TDPetRuntime.wurst':
        expected = exact_replace(expected, 'import TDEnemyMechanicRuntime\n', 'import TDEnemyMechanicRuntime\nimport TDBossRewardRules\nimport TDWaveFlowState\n')
        expected = expected.replace(source_function(expected, 'tdPetHandlePlayerLeave'), '', 1)
        expected = exact_replace(expected, '\tregisterPlayerEvent(EVENT_PLAYER_LEAVE, function tdPetHandlePlayerLeave)\n', '')
        new = source_function(after, 'tdPetHandleBossBallCompensation')
        marker = 'public function tdPetTryOpenCollection'
        # Preserve the surrounding bytes, independently of the inserted function's position.
        require(after.count(new) == 1, 'Duplicate Boss ball entry')
        require(after.replace(new, '', 1) == expected, 'Unrelated pet runtime source changed')
        return after
    elif path == 'pets/TDPetWild.wurst':
        old = source_function(expected, 'tdPetSpawnWild')
        new = source_function(after, 'tdPetSpawnWild')
        guard = '\tif not tdIsLanePlayer(lane) or wave < 1 or wave > 25 or tdWaveBossEnemyCount(wave) > 0 or species < 1 or species > 3\n\t\treturn null\n'
        require(new.count(guard) == 1 and new.replace(guard, '') == old, 'Wild spawn changed outside hard Boss rejection')
        expected = expected.replace(old, new, 1)
        expected = exact_replace(expected, 'wave < 1 or wave > 25\n', 'wave < 1 or wave > 25 or tdWaveBossEnemyCount(wave) > 0\n')
        expected = exact_replace(expected, 'public function tdPetWildOnWave(int lane, int wave)\n', 'public function tdPetWildOnWave(int lane, int wave)\n\tif tdWaveBossEnemyCount(wave) > 0\n\t\treturn\n')
        new = source_function(after, 'tdPetWildHasCaptureWindow')
        require(after.replace(new, '', 1) == expected, 'Unrelated wild-pet source/deadline changed')
        return after
    else:
        return None
    require(after == expected, path + ': source changed outside exact approved edits')
    return expected


def verify_source_delta(current, baseline, approved_source_owners):
    require(set(approved_source_owners) <= CHANGED_OWNERS, 'Unknown approved source owner')
    require(set(baseline) <= set(current), 'Production source removed')
    require(set(current) - set(baseline) == NEW_OWNERS, 'Unexpected/missing new production source')
    changed = {path for path in current if current[path] != baseline.get(path)}
    require(changed <= set(approved_source_owners), 'Changed source lacks explicit owner approval: ' + ', '.join(sorted(changed - set(approved_source_owners))))
    changed_functions, changed_classes, new_symbols = set(), set(), set()
    for path in sorted(changed):
        after, before = current[path], baseline.get(path, '')
        package = re.fullmatch(r'package (\w+)', after.splitlines()[0])
        require(package and package[1] == Path(path).stem, 'Source package/owner mismatch: ' + path)
        # Imports can change initialization order; only exact intended additions
        # are allowed, and every existing import keeps its relative order.
        if path not in NEW_OWNERS:
            prior_imports = [line for line in before.splitlines() if line.startswith('import ')]
            imports = [line for line in after.splitlines() if line.startswith('import ')]
            allowed_imports = {
                'TDGame.wurst': {'import TDWaveFlowState', 'import TDEnemyMechanicData', 'import TDBossDarkTideRuntime', 'import public TDBossTransitionHook', 'import GameTimer', 'import TDBossRewardRules', 'import TDBossRewardRuntime'},
                'TDHud.wurst': {'import TDWaveFlowState', 'import GameTimer'},
                'TDInit.wurst': {'import RegisterEvents'},
                'TDSpawn.wurst': {'import TDWaveFlowState', 'import Table'},
                'TDState.wurst': {'import TDWaveFlowState'},
                'enemies/TDEnemyMechanicRuntime.wurst': {'import GameTimer', 'import TDBossDarkTideRuntime', 'import TDWaveFlowState'},
                'pets/TDPetRuntime.wurst': {'import TDBossRewardRules', 'import TDWaveFlowState'},
                'pets/TDPetState.wurst': {'import TDEnemyMechanicData'},
                'towers/TDTowerRuntime.wurst': {'import TDBossDarkTideRuntime'},
            }.get(path, set())
            require([line for line in imports if line not in allowed_imports] == prior_imports,
                    path + ': existing import order/initialization changed')
            require(set(imports) - set(prior_imports) <= allowed_imports,
                    path + ': unapproved import dependency')
        if path != 'towers/TDTowerRuntime.wurst':
            require(not re.search(r'\b(?:UnitDamageTarget|damageTarget|SetUnitArmor|BlzSetUnitAttackCooldown)\s*\(', after),
                    path + ': unexpected native damage/combat mutation')
        if path not in ('TDWaves.wurst', 'enemies/TDEnemyMechanicData.wurst'):
            require(re.findall(r"'(.{4})'", after) == re.findall(r"'(.{4})'", before),
                    path + ': unexpected source rawcode')
        a, b = declarations(after), declarations(before)
        if path in NEW_OWNERS:
            require(set(a) == NEW_DECLS[path], path + ': unexpected/missing task declaration')
            permitted = set(a)
        elif expected_partial(path, before, after) is not None:
            permitted = {name for name in a if a[name] != b.get(name)}
        else:
            require(set(a) - set(b) == NEW_DECLS.get(path, set()), path + ': unexpected/missing new declaration')
            permitted = CHANGED_DECLS.get(path, set()) | NEW_DECLS.get(path, set())
            removed = set(b) - set(a)
            require(removed <= REMOVED_DECLS.get(path, set()), path + ': unrelated declaration removed: ' + ', '.join(removed))
            for name in set(a) & set(b):
                require(name in permitted or a[name] == b[name], path + ': unrelated declaration changed: ' + name)
            # Do not grant arbitrary global/rawcode changes because a package changed.
            def residual(text, decls):
                for pieces in decls.values():
                    for piece in pieces:
                        text = text.replace(piece, '', 1)
                return [line for line in text.splitlines() if line.strip() and not line.startswith(('import ', '//'))]
            old_residual, new_residual = residual(before, b), residual(after, a)
            allowed_removed = {"public constant int TD_ENEMY_GUARD_ARMOR_ABILITY_ID = 'Emar'", 'public constant int TD_ENEMY_GUARD_ARMOR_BONUS = 4',
                'TDEnemyGuardLink array tdEnemyGuardLinks'}
            old_residual = [line for line in old_residual if line not in allowed_removed]
            require(all(line in new_residual for line in old_residual), path + ': unrelated global/rawcode changed')
            added_lines = [line for line in new_residual if line not in old_residual]
            # Only task-specific state can be added. No unrelated bare rawcode can enter.
            allowed_new = {'TDGame.wurst': {'unit array tdBossUnits', 'boolean tdEnemyDeathWatcherReady = false'},
                'TDSpawn.wurst': {'constant Table tdEnemyMatchEpochs = new Table()'},
                'TDHud.wurst': set(), 'enemies/TDEnemyMechanicRuntime.wurst': set(),
                'enemies/TDEnemyMechanicState.wurst': set(),
                'enemies/TDEnemyMechanicObjectGen.wurst': set(),
                'enemies/TDEnemyMechanicData.wurst': {
                    "public constant int TD_BOSS_DARK_TIDE_ABILITY_ID = 'Ebtd'", 'public constant real TD_BOSS_DARK_TIDE_RADIUS = 250.0',
                    'public constant real TD_BOSS_DARK_TIDE_DURATION = 3.0', 'public constant real TD_BOSS_DARK_TIDE_ATTACK_SPEED = -0.20',
                    'public constant int TD_BOSS_EVENT_WARNING = 1', 'public constant int TD_BOSS_EVENT_DARK_TIDE = 2',
                    'public constant int TD_BOSS_EVENT_ENRAGE = 4'}}.get(path, set())
            require(set(added_lines) <= allowed_new, path + ': unexpected production global: ' + repr(set(added_lines) - allowed_new))
        for name in permitted:
            for piece in a.get(name, []) + b.get(name, []):
                if re.search(r'^(?:public )?(?:class|interface) ', piece):
                    changed_classes.add(name)
                else:
                    changed_functions.add(name.split('.')[-1])
        for piece in a.values():
            for declaration in piece:
                new_symbols.update(re.findall(r'^\s*(?:public |private )?(?:constant )?(?:int|real|boolean|unit|Table|TDBossTransitionHook|LinkedList<[^>]+>) (?:array(?:\[\d+\])? )?(\w+)', declaration, re.M))
    for path, expected in SOURCE_OWNER_TEMPLATES.items():
        require(sha(current[path].encode()) == expected, path + ': changed source owner differs from exact approved template')
    for key, expected in SOURCE_DECLARATION_TEMPLATES.items():
        path, name = key.split('::', 1)
        require(sha(''.join(declarations(current[path])[name]).encode()) == expected, key + ': changed source body differs from exact approved template')
    verify_source_contract(current)
    return {'changed_owners': sorted(changed), 'changed_functions': sorted(changed_functions),
            'changed_classes': sorted(changed_classes), 'source_sha256': {p: sha(current[p].encode()) for p in sorted(current)}}


def verify_source_contract(source):
    def body(path, name):
        return source_function(source[path], name)
    hook = source['TDBossTransitionHook.wurst']
    for text in ('function onReady(int completedWave, int transitionToken) returns boolean',
                 'function onRelease(int transitionToken, int reason)',
                 'TD_TRANSITION_COMPLETED = 1', 'TD_TRANSITION_TIME_LIMIT = 2',
                 'TD_TRANSITION_ABORTED = 3', 'TD_BOSS_TRANSITION_TIME_LIMIT = 120.0'):
        require(text in hook, 'Hook contract mismatch: ' + text)
    release = body('TDWaveFlowState.wurst', 'tdFlowReleaseTransition')
    ordered(release, ('if not tdFlowTransitionIsHeld(token)', 'tdFlowTransitionState = 2',
        'tdFlowHook.onRelease(token, reason)', 'tdFlowTransitionState = 0'), 'Atomic release')
    reset = body('TDWaveFlowState.wurst', 'tdResetWaveFlowState')
    for text in ('tdFlowMatchEpoch += 1', 'tdFlowScheduleToken += 1', 'tdFlowTransitionToken += 1',
                 'tdFlowSpawnGeneration[lane] += 1', 'TD_TRANSITION_ABORTED'):
        require(text in reset, 'Reset must invalidate monotonic token: ' + text)
    prepare = body('TDWaveFlowState.wurst', 'tdFlowPrepareBoss')
    require('tdFlowSpawnGeneration' not in prepare and 'tdFlowSpawnBusy' not in prepare, 'Preparation cancels old legitimate production')
    preparation = body('TDGame.wurst', 'tdPrepareBossRound')
    require(not re.search(r'\b(?:tdHandleEnemyLeak|tdClearLaneEnemies|remove|kill|tdFlowCancelLane|tdPetWildTransition)\s*\(', preparation), 'Preparation prematurely withdraws/leaks old enemies or pets')
    ready = body('TDGame.wurst', 'tdBossPreparationReady')
    for text in ('tdContinuingLanesEmpty()', 'tdPetWildHasCaptureWindow()', 'tdGetResolvedWave(lane) < wave - 1'):
        require(text in ready, 'Preparation missing true drain gate: ' + text)
    resume = body('TDGame.wurst', 'tdResumeBossTransition')
    ordered(resume, ('tdIsGameOver()', 'tdContinuingLanesEmpty()', 'tdFlowReleaseTransition(transitionToken, TD_TRANSITION_COMPLETED)', 'epoch != tdFlowEpoch()', 'tdStartGlobalWave(wave + 1)'), 'Synchronous held resume')
    require('tdScheduleWaveAfterDelay' not in resume and 'doAfter(' not in resume, 'Held resume adds an unauthorized delay')
    intermission = body('TDGame.wurst', 'tdBeginBossIntermission')
    ordered(intermission, ('tdFlowHoldTransition(wave)', 'tdFlowCallTransitionReady(wave, token)', 'if held',
        'doAfter(TD_BOSS_TRANSITION_TIME_LIMIT)', 'tdFlowReleaseTransition(token, TD_TRANSITION_TIME_LIMIT)', 'tdStartGlobalWave(wave + 1)', 'tdScheduleWaveAfterDelay(wave, 30.0)'), 'Held timeout/direct versus ordinary delay')
    spawn = body('TDGame.wurst', 'tdStartPreparedBoss')
    require(spawn.count('tdCreateEnemy(') == 1 and 'tdEnemyMechanicIsRegistered(boss)' in spawn, 'Exactly one successfully registered Boss per continuing lane required')
    ordered(spawn, ('tdFlowStartBoss(wave)', 'tdCreateEnemy(', 'tdEnemyMechanicIsRegistered(boss)', 'tdFlowActivateBoss('), 'Boss deadline only after registration')
    claim = body('TDGame.wurst', 'tdClaimEnemyKill')
    ordered(claim, ('tdEnemyBelongsToCurrentMatch(enemy)', 'tdFlowClaimBossResult(playerId, wave, TD_BOSS_RESULT_KILLED)', 'tdFlowClaimBossReward(', 'tdMarkEnemyKilled(enemy)'), 'Atomic kill result/reward claim')
    death = body('TDGame.wurst', 'tdHandleEnemyDeath')
    ordered(death, ('not tdClaimEnemyKill(enemy)', 'tdGainGold(', 'tdEvolutionRecordKill(', 'tdHandlePureBossLoot('), 'Reward chain after legitimate claim')
    require(death.count('tdHandlePureBossLoot(') == 1, 'Boss loot duplicated')
    fail = body('TDGame.wurst', 'tdSettleBossFailure')
    ordered(fail, ('tdFlowClaimBossResult(', 'tdMarkEnemyLeaked(', 'tdLoseLife(playerId, 3)', 'tdEnemyMechanicUnregister(', 'enemy.kill()', 'tdForgetEnemyMatch('), 'Atomic failure before synchronous death')
    require(not any(name in fail for name in ('tdBossKillCompensation', 'tdHandlePureBossLoot', 'tdEvolutionRecordKill')), 'Failure grants kill benefits')
    leave_setup = body('TDInit.wurst', 'tdSetupLanePlayerLeaveWatcher')
    ordered(leave_setup, ('if tdLanePlayerLeaveWatcherReady', 'return false',
        'tdLanePlayerLeaveWatcherReady = true', 'if not compiletime',
        'registerPlayerEvent(EVENT_PLAYER_LEAVE, function tdHandleLanePlayerLeaveEvent)', 'return true'),
        'One lifetime lane-leave listener')
    require(sum(text.count('registerPlayerEvent(EVENT_PLAYER_LEAVE,') for text in source.values()) == 1,
        'Leave lifecycle registered outside the single startup owner')
    require('tdHandleLanePlayerLeft(GetPlayerId(GetTriggerPlayer()))' in
        body('TDInit.wurst', 'tdHandleLanePlayerLeaveEvent'), 'Leave callback bypasses unified lane close')
    require(not re.search(r'^import (?:initlater )?TDGame$', source['pets/TDPetRuntime.wurst'], re.M),
        'Pet runtime regained a reverse Game dependency')
    for path, name in (('TDInit.wurst', 'tdStartGame'), ('TDState.wurst', 'tdResetState')):
        require('tdLanePlayerLeaveWatcherReady' not in body(path, name), 'Match reset re-registers persistent leave listener')
    startup = body('TDInit.wurst', 'tdRunGameplayStartup')
    ordered(startup, ('tdSetupPets()', 'tdSetupLanePlayerLeaveWatcher()', 'tdStartLaneWaypointWatcher()'),
        'Leave listener before game watchers')
    leave = body('TDGame.wurst', 'tdHandleLanePlayerLeft')
    ordered(leave, ('tdPetMarkPlayerLeft(playerId)', 'tdPetLaneDefeated(playerId)',
        'tdIsLaneFinished(playerId)', 'tdCloseDefeatedLane(playerId)', 'tdTryScheduleNextWave(tdGetGlobalWave())'),
        'Finished result preserved, unfinished leave closes before advance')
    for name in ('tdOrderEnemyAlongLane', 'tdAdvanceEnemyWaypoint', 'tdLaneEnemyCheckEnum'):
        values = declarations(source['TDSpawn.wurst'])[name]
        require(any('tdEnemyBelongsToCurrentMatch(enemy)' in x for x in values), 'Trial/stale enemy isolation missing: ' + name)
    current_match = body('TDSpawn.wurst', 'tdEnemyBelongsToCurrentMatch')
    require('tdEnemyMatchEpochs.hasInt(' in current_match and '== tdFlowEpoch()' in current_match, 'Current-match registry lost')
    dark = source['enemies/TDBossDarkTideRuntime.wurst']
    for text in ('tower.addAbility(TD_BOSS_DARK_TIDE_ABILITY_ID)', 'tower.removeAbility(TD_BOSS_DARK_TIDE_ABILITY_ID)',
                 'record.matchEpoch != tdFlowEpoch()', '!= record.bossGeneration', 'GetUnitTypeId(record.tower) != record.towerType'):
        require(text in dark, 'Dark-tide owner cleanup missing: ' + text)
    require(not re.search(r'(?i)(?:get|set|restore|cache)\w*AttackSpeed|tdPet\w*(?:Speed|Bonus)|bloodlust', '\n'.join(x for x in dark.splitlines() if not x.lstrip().startswith('//'))), 'Dark tide touches aggregate/equipment/pet/bloodlust attack speed')
    require('setAttackSpeedIncrease(1, TD_BOSS_DARK_TIDE_ATTACK_SPEED)' in source['enemies/TDEnemyMechanicObjectGen.wurst'] and 'setItemAbility(true)' in source['enemies/TDEnemyMechanicObjectGen.wurst'], 'Independent native item attack-speed ability required')
    hud = source['TDHud.wurst']
    require('setRowCount(tdCountActiveLanes() + 5 + TD_DAMAGE_HUD_ROWS)' in hud and 'setColumnCount(TD_DAMAGE_HUD_COLUMNS)' in hud, 'HUD row count/four-column ranking changed')
    ordered(body('TDHud.wurst', 'tdHudSetBossIcon'), ('tdIsGameOver() ? ""', 'setItemIcon(row, 1, icon)', 'setStyle(false, icon != "")'), 'HUD icon cleanup/style')
    for text in ('Emar', 'TDEnemyGuardLink', 'tdEnemyGuardArmorEnabled'):
        require(all(text not in source[p] for p in ('enemies/TDEnemyMechanicData.wurst', 'enemies/TDEnemyMechanicState.wurst', 'enemies/TDEnemyMechanicRuntime.wurst', 'enemies/TDEnemyMechanicObjectGen.wurst')), 'Old guard armor owner remains: ' + text)
    loot = body('items/TDBossRewardRuntime.wurst', 'tdHandlePureBossLoot')
    ordered(loot, ('tdFlowBossResult(lane, wave) != TD_BOSS_RESULT_KILLED', 'new TDBossLootPlan(', 'tdBossNormalDropAttempts(wave)', 'plan.appendBonus(', 'plan.sharedCount'), 'Frozen shared loot plan followed by independent slot')
    require('qualityRolls' not in loot and 'tdHandleEnemyDrop' not in loot, 'Removed-enemy lucky rolls/second Boss guarantee restored')
    require('not tdFlowClaimBossLoot(lane, wave)' in loot, 'Loot can precede atomic claim or draw twice')
    ball = body('pets/TDPetRuntime.wurst', 'tdPetHandleBossBallCompensation')
    ordered(ball, ('TD_BOSS_RESULT_KILLED', 'tdFlowClaimBossBallCompensation', 'tdBossBallDropAttempts(wave)', 'tdBossBallDropSucceeds(', 'tdPetTakeDropBudget(', 'tdPetBallOwners.saveInt('), 'Original quota/owned ground ball')


def icon_paths():
    return [prefix + 'TDBoss' + stem + '.blp' for stem in ICON_STEMS
            for prefix in ('war3mapImported\\BTN', 'ReplaceableTextures\\CommandButtonsDisabled\\DISBTN')]


def verify_icons(artifact, source):
    root = source_root(source).parent
    checked = {}
    for stem in ICON_STEMS:
        for disabled, prefix in enumerate(('war3mapImported\\BTN', 'ReplaceableTextures\\CommandButtonsDisabled\\DISBTN')):
            path = prefix + 'TDBoss' + stem + '.blp'
            data = artifact.extract(path)
            require(sha(data) == ICON_SHA[stem][disabled], 'Approved exact Boss BLP bytes changed: ' + path)
            require((root / 'imports' / Path(path.replace('\\', '/'))).read_bytes() == data, 'Source/packed Boss icon differs: ' + path)
            images = decode_blp(data, path)
            require(all(im.getchannel('A').getextrema() == (255, 255) for im in images), 'Boss BLP must be opaque at all seven mips')
            checked[path] = sha(data)
    return checked


def value(obj, field, level=0, column=0):
    require((field, level, column) in obj.fields, 'Missing exact object field: ' + repr((field, level, column)))
    return obj.fields[field, level, column].value


def verify_object_delta(current, baseline):
    require(set(current) == set(baseline), 'Object member table set changed')
    expected_boss_fields = {'uhpm', 'udef', 'umvs', 'umas', 'unam', 'uico', 'uabi'}
    modified = []
    for filename in baseline:
        before, after = baseline[filename], current[filename]
        removed = {'Emar'} if filename == 'war3map.w3a' else set()
        added = {'Ebtd'} if filename == 'war3map.w3a' else set()
        require(set(after) == (set(before) - removed) | added, filename + ': unexpected object/rawcode delta')
        require([x for x in after if x not in added] == [x for x in before if x not in removed], filename + ': surviving object order changed')
        for code in set(after) & set(before):
            old, obj = before[code], after[code]
            require((obj.table, obj.identity) == (old.table, old.identity), code + ': parent/identity changed')
            allowed = expected_boss_fields if filename == 'war3map.w3u' and code in {'uB08', 'uB16', 'uB24', 'uB32'} else {'umas'} if filename == 'war3map.w3u' and code == 'uG32' else set()
            if filename == 'war3map.w3a' and code == 'A130':
                verify_evolution_object(obj, old)
                modified.append(code)
                continue
            if filename == 'war3map.w3a' and code == 'AeEV':
                require((obj.table, obj.identity) == (1, b'AOcrAeEV'), 'AeEV identity/table changed')
                require(list(obj.fields) == list(old.fields), 'AeEV field set/order changed')
                for key, field in obj.fields.items():
                    prior = old.fields[key]
                    if key == ('aub1', 1, 0):
                        require(prior.kind == 3 and prior.value.count('累计250击杀') == 1, 'AeEV formal threshold text changed')
                        wanted = prior.value.replace('累计250击杀', '累计220击杀', 1)
                        require((field.kind, field.value, field.raw) == (3, wanted,
                            prior.raw[:16] + wanted.encode() + b'\0' + prior.raw[-4:]),
                            'AeEV exact threshold field/encoding changed')
                    else:
                        require(field == prior, 'AeEV unrelated field changed: ' + repr(key))
                modified.append(code)
                continue
            require(set(obj.fields) - set(old.fields) <= {(x, 0, 0) for x in allowed}, code + ': unrelated object fields added')
            require(set(old.fields) <= set(obj.fields), code + ': unrelated object fields removed')
            for key in set(old.fields) & set(obj.fields):
                new_field, old_field = obj.fields[key], old.fields[key]
                if key[0] not in allowed:
                    require(new_field == old_field, code + ': unrelated object field changed: ' + repr(key))
                else:
                    require((new_field.kind, new_field.raw[:8], new_field.raw[-4:]) == (old_field.kind, old_field.raw[:8], old_field.raw[-4:]), code + ': field encoding/end marker changed')
            if obj.encoded() != old.encoded():
                modified.append(code)
    units, abilities = current['war3map.w3u'], current['war3map.w3a']
    for wave, hp, armor, name, stem in zip(BOSS_WAVES, BOSS_HP, BOSS_ARMOR, BOSS_NAMES, ICON_STEMS):
        code = f'uB{wave:02d}'
        boss = units[code]
        require(value(boss, 'uhpm') == hp and value(boss, 'udef') == armor and value(boss, 'unam') == name, code + ': exact approved HP/armor/name mismatch')
        require(value(boss, 'uico') == 'war3mapImported\\BTNTDBoss' + stem + '.blp', code + ': exact Boss icon binding mismatch')
        require(value(boss, 'uabi') == '', code + ': Emar/foreign attached ability remains')
        require(value(boss, 'umas') == int(value(boss, 'umvs') * (1.30 if wave == 8 else 1.15 if wave == 32 else 1.0) + 0.5), code + ': exact mechanic maximum speed changed')
    require(value(units['uG32'], 'umas') == value(units['uG32'], 'umvs'), 'Obsolete guard sprint max speed remains')
    dark = abilities['Ebtd']
    require(dark.identity == b'AIsxEbtd' and dark.table == 1, 'Ebtd must be a new native AttackSpeedIncrease item ability')
    expected = {('wurs', 0, 0): (0, 42), ('anam', 0, 0): (3, '暗潮攻速削减'), ('Isx1', 1, 1): (2, struct.unpack('<f', struct.pack('<f', -0.20))[0]),
                ('aite', 0, 0): (0, 1), ('achd', 0, 0): (0, 0)}
    require(set(dark.fields) == set(expected), 'Ebtd unexpected combat/display field')
    for key, (kind, wanted) in expected.items():
        field = dark.fields[key]
        payload = wanted.encode() + b'\0' if kind == 3 else struct.pack('<i' if kind == 0 else '<f', wanted)
        expected_raw = key[0].encode() + struct.pack('<III', kind, key[1], key[2]) + payload + b'\0' * 4
        require((field.kind, field.value, field.raw) == (kind, wanted, expected_raw), 'Ebtd exact native field/encoding mismatch: ' + str(key))
    require('Emar' not in abilities, 'Emar remains packaged')
    return {'modified_objects': sorted(modified), 'added': ['Ebtd'], 'removed': ['Emar']}


def verify_evolution_object(current, baseline):
    require((current.table, current.identity) == (baseline.table, baseline.identity), 'A130 identity changed')
    require(value(current, 'alev') == 475, 'A130 must expose exactly 475 real-count levels')
    expected_keys = {k for k in baseline.fields if k[1] <= 475}
    require(set(current.fields) == expected_keys, 'A130 field/level coverage changed')
    require(list(current.fields) == [k for k in baseline.fields if k in expected_keys], 'A130 surviving field order changed')
    for key, field in current.fields.items():
        old = baseline.fields[key]
        if key == ('alev', 0, 0):
            wanted = 475
        elif key[0] == 'aub1':
            wanted = old.value.replace('达到250击杀', '达到220击杀')
        else:
            require(field == old, 'A130 unrelated progress/carrier field changed: ' + repr(key))
            continue
        payload = wanted.encode() + b'\0' if field.kind == 3 else struct.pack('<i', wanted)
        require(field.kind == old.kind and field.value == wanted and field.raw == old.raw[:16] + payload + old.raw[-4:], 'A130 exact threshold/count encoding changed')
    for kills in (0, 219, 220, 221, 474):
        require(value(current, 'atp1', kills + 1) == f'累计击杀：{kills}', 'A130 real kill progress mismatch')


def verify_archive_delta(current, baseline):
    after, before = members(current), members(baseline)
    additions = {p.casefold(): p for p in icon_paths()}
    require(set(after) == set(before) | set(additions), 'Unexpected/missing MPQ resource')
    require(not set(additions) & set(before), 'Formal baseline already contains Boss icon resources')
    mutable = {'war3map.j', 'war3map.w3u', 'war3map.w3a', 'war3map.w3i', 'war3map.imp', '(listfile)'}
    for key, (old_name, old) in before.items():
        name, data = after[key]
        require(name == old_name, 'MPQ member spelling changed')
        if key in mutable:
            if key == 'war3map.w3i':
                require(normalize_info(data) == normalize_info(old), 'Map metadata changed beyond two display timestamps')
            continue
        require(data == old, 'Unrelated MPQ member changed: ' + name)
    for key, name in additions.items():
        require(after[key][0] == name, 'Boss icon member spelling changed')
    def imports(data):
        from VerifySemanticIconArtifact import Reader
        r = Reader(data)
        require(r.integer() == 1, 'Unexpected import table version')
        rows = [(r.take(1), r.string()) for _ in range(r.integer())]
        require(r.offset == len(data) and len({name.casefold() for _, name in rows}) == len(rows), 'Import coverage/duplicate/trailing record')
        return rows
    a, b = imports(after['war3map.imp'][1]), imports(before['war3map.imp'][1])
    require([r for r in a if r[1].casefold() not in additions] == b, 'Existing import rows/order/flags changed')
    require({p for flag, p in a if p.casefold() in additions} == set(additions.values()) and all(flag == b'\r' for flag, p in a if p.casefold() in additions), 'Eight exact custom import flags/paths required')
    def listfile(data):
        return data.decode('utf-8-sig').splitlines()
    a, b = listfile(after['(listfile)'][1]), listfile(before['(listfile)'][1])
    require([p for p in a if p.casefold() not in additions] == b, 'Existing listfile rows/order changed')
    return {'member_count': len(after), 'new_resources': sorted(additions.values())}



def draft_jass_templates(script, baseline_script, source):
    """Produce a review input, never an automatically approved compiled delta.

    The caller must extract a real authorized final build, independently review
    its source/JASS integration and inherited preservation, then explicitly
    approve this exact draft and supply a verifiable review reference. A
    candidate cannot override built-in source checkpoint templates with it.
    """
    return {'schema_version': 1, 'review_status': 'PENDING', 'review_reference': None,
        'candidate_script_sha256': sha(script.encode()),
        'formal_script_sha256': sha(baseline_script.encode()),
        'source_sha256': {p: sha(source[p].encode()) for p in sorted(source)},
        'functions': {n: m[0] for n, m in functions(script).items()},
        'global_declarations': script.split('globals\n', 1)[1].split('endglobals', 1)[0].splitlines()}


def verify_reviewed_jass_templates(script, baseline_script, source, template):
    require(set(template) == {'schema_version', 'review_status', 'review_reference',
        'candidate_script_sha256', 'formal_script_sha256', 'source_sha256',
        'functions', 'global_declarations'}, 'Compiled template schema must be closed')
    require(template['schema_version'] == 1 and template['review_status'] == 'APPROVED' and
            isinstance(template['review_reference'], str) and bool(template['review_reference'].strip()),
            'Compiled templates have not been independently approved')
    require(template['source_sha256'] == {p: sha(source[p].encode()) for p in sorted(source)},
            'Reviewed compiled templates are tied to different complete source bytes')
    require(template['formal_script_sha256'] == sha(baseline_script.encode()),
            'Reviewed compiled templates reference a different immutable formal map')
    # Compare full text before checking its digest, for an actionable owner.
    actual = {name: fn[0] for name, fn in functions(script).items()}
    require(set(actual) == set(template['functions']), 'Reviewed compiled function set changed')
    for name, expected in template['functions'].items():
        require(actual[name] == expected, 'Compiled function differs from exact reviewed template: ' + name)
    actual_globals = script.split('globals\n', 1)[1].split('endglobals', 1)[0].splitlines()
    require(actual_globals == template['global_declarations'], 'Compiled globals differ from exact reviewed declarations')
    require(template['candidate_script_sha256'] == sha(script.encode()),
            'Outside-function/header/ordering JASS differs from exact reviewed script')
    return {'review_reference': template['review_reference'], 'exact_functions': len(actual),
            'exact_global_declarations': len(actual_globals), 'script_sha256': template['candidate_script_sha256']}


def source_line_maps(current, baseline):
    maps = {}
    for path in set(current) & set(baseline):
        new, old = current[path].splitlines(), baseline[path].splitlines()
        mapping = {}
        for block in difflib.SequenceMatcher(a=old, b=new, autojunk=False).get_matching_blocks():
            for offset in range(block.size):
                mapping[block.b + offset + 1] = block.a + offset + 1
        maps[Path(path).stem] = mapping
    return maps


def diagnostic_view(text, maps):
    """Only source-proven exact diagnostic line shifts; never erase strings."""
    pattern = re.compile(r'"((?:when calling [\w.]+|via function reference) (\w+), line (\d+))"')
    # Standard diagnostic spelling has "in PACKAGE" for method calls.
    pattern = re.compile(r'"((?:when calling [\w.]+ in|via function reference) (\w+), line (\d+))"')
    def convert(match):
        message, package, line = match.groups()
        if package not in maps or int(line) not in maps[package]:
            return match[0]
        new = maps[package][int(line)]
        return '"' + message.rsplit(' ', 1)[0] + ' ' + str(new) + '"'
    return pattern.sub(convert, text)


def local_alpha_view(current, baseline):
    """Prove declaration type/order and one bijection covering every use."""
    def decls(text):
        signature = re.search(r'^function \w+ takes ([^\n]*) returns', text)[1]
        parameters = [] if signature == 'nothing' else [tuple(p.strip().split()) for p in signature.split(',')]
        locals_ = re.findall(r'^\s*local (\w+) (\w+)\b', text, re.M)
        return parameters + locals_
    a, b = decls(current), decls(baseline)
    require([t for t, _ in a] == [t for t, _ in b], 'Compiler local/parameter types/order changed')
    mapping = {n: o for (_, n), (_, o) in zip(a, b)}
    require(len(mapping) == len(a) and len(set(mapping.values())) == len(b), 'Compiler local alpha map not bijective')
    # Source variable stem stays stable. Only compiler-added numeric suffixes vary.
    stem = lambda n: re.sub(r'_\d+$', '', n) if not re.fullmatch(r'temp\d+(?:_\w+)?', n) else 'compilerTemp'
    require(all(stem(n) == stem(o) for n, o in mapping.items()), 'Non-compiler source local renamed')
    return TOKEN.sub(lambda m: m[0] if m[0].startswith('"') else mapping.get(m[0], m[0]), current)


def changed_jass_name(name, proof):
    changed = set(proof['changed_functions'])
    classes = set(proof['changed_classes'])
    if name in changed or re.sub(r'_\d+$', '', name) in changed:
        return True
    for cls in classes:
        if name.startswith((cls + '_', 'construct_' + cls, 'new_' + cls, 'alloc_' + cls,
                            'dealloc_' + cls, 'destroy' + cls, 'dispatch_' + cls + '_')):
            return True
    # Closure owners are concrete source packages; this cannot cover unrelated
    # equipment/pet combat packages merely because they share an abstract base.
    owners = {Path(p).stem for p in proof['changed_owners'] if p in ('TDGame.wurst', 'TDSpawn.wurst', 'TDHud.wurst', 'enemies/TDEnemyMechanicRuntime.wurst')}
    if any(re.search(r'_' + re.escape(owner) + r'(?:_\d+)?$', name) for owner in owners):
        return bool(re.match(r'(?:call_|alloc_|dealloc_|destroy|construct_|new_|init_)', name))
    return False


# These compiler changes were independently reviewed against this one real
# combined build. They are not package/prefix exemptions or future build rules.
COMBINED_06_SCRIPT_SHA = '7228cc50df34fe4fb438c04bc613b5961016dbf0874a25622c26661c67671ed0'
MANAGER_654_SCRIPT_SHA = 'e8d2ac4c0f26bbd7ae18749cfca66c2cc3b5252f86f9a688b3bbb362158a7998'
COMBINED_06_REVIEW = 'Astra read-only review 2026-10-12 combined-06; exact pending SHA3934230378985686bfba8c423660baa1256a8c6e9166751723a3925af1c58a7d'
COMBINED_06_EXACT_COMPILER_FUNCTIONS = frozenset('''
TDEnemyGuardLink_init TDEnemyGuardLink_onDestroy TDEnemyGuardLink_protects
TDPet_hasActiveExcept TDPet_quality TDPet_qualityAt TDPet_rollSkill TDPet_setSkill TDPet_skillAt TDPet_skillPower
alloc_CallbackSingle_doAfter_TDGame_1 alloc_CallbackSingle_doAfter_TDGame_2 alloc_TDEnemyGuardLink alloc_TDEnemyMechanicState
bridge_init_TDBossDarkTideRuntime bridge_init_TDSpawn bridge_tdHandleLanePlayerLeaveEvent bridge_tdLaneEnemyCheckEnum
call_doPeriodically_TDPetCombat construct_TDEnemyGuardLink construct_TDPet dealloc_TDEnemyGuardLink destroyTDEnemyGuardLink
dispatch_CallbackPeriodic_CallbackPeriodic_call dispatch_CallbackSingle_CallbackSingle_call
dispatch_TDEnemyGuardLink_TDEnemyGuardLink_protects dispatch_TDEnemyGuardLink_destroyTDEnemyGuardLink
initGlobals init_TDBossDarkTideRuntime init_TDBossRewardRules init_TDBossTransitionHook init_TDEnemyMechanicData
init_TDInit init_TDTowerEvolutionState init_TDWaveFlowState main multiboard_setItemIcon multiboarditem_setIcon multiboarditem_setStyle
new_TDEnemyGuardLink tdCreateArcherSplitArrowVolley tdEnemyGuardArmorEnabled tdEnemyMechanicSyncArmor
tdLaneHasLivingEnemies tdLaneHasLivingEnemies_1 tdMarkLaneWaveDrop tdPetHandlePlayerLeave
'''.split())
COMBINED_06_EXACT_DELETIONS = frozenset('''
TDEnemyGuardLink_init TDEnemyGuardLink_onDestroy TDEnemyGuardLink_protects alloc_TDEnemyGuardLink
construct_TDEnemyGuardLink dealloc_TDEnemyGuardLink destroyTDEnemyGuardLink
dispatch_TDEnemyGuardLink_TDEnemyGuardLink_protects dispatch_TDEnemyGuardLink_destroyTDEnemyGuardLink
new_TDEnemyGuardLink tdEnemyGuardArmorEnabled tdEnemyMechanicSyncArmor tdPetHandlePlayerLeave
'''.split())


def prove_jass_delta(script, baseline, source, baseline_source, proof, reviewed_jass_templates=None):
    """Preserve every unrelated function, declaration and script boundary.

    Allocator IDs may move only under their same named owner, with the entire
    allocator body preserved. Type comparisons use that very same bijection.
    Unknown abstract range boundaries, generated global aliases and dispatcher
    reshaping are reported as blockers; they are not automatically permitted.
    """
    if proof['changed_owners']:
        require(reviewed_jass_templates is not None, 'Final compiled delta blocked: a real build and explicitly reviewer-approved exact JASS templates are required')
        verify_reviewed_jass_templates(script, baseline, source, reviewed_jass_templates)
    combined_06 = bool(reviewed_jass_templates and
        reviewed_jass_templates['review_reference'] == COMBINED_06_REVIEW and
        sha(script.encode()) == COMBINED_06_SCRIPT_SHA and sha(baseline.encode()) == MANAGER_654_SCRIPT_SHA)
    exact_compiler = COMBINED_06_EXACT_COMPILER_FUNCTIONS if combined_06 else frozenset()
    if combined_06:
        require(len(source) == 64 and len(exact_compiler) == 47 and len(COMBINED_06_EXACT_DELETIONS) == 13,
            'Exact combined-06 reviewed source/compiler scope changed')
        actual_functions = functions(script)
        require(not COMBINED_06_EXACT_DELETIONS & set(actual_functions), 'Reviewed deleted compiler function reappeared')
        for name in exact_compiler - COMBINED_06_EXACT_DELETIONS:
            require(name in actual_functions and actual_functions[name][0] == reviewed_jass_templates['functions'][name],
                'Exact reviewed compiler adaptation changed: ' + name)
    script, math_evidence = inherited_script_view(script, baseline)
    current, before = functions(script), functions(baseline)
    new_ids, old_ids = allocations(script), allocations(baseline)
    mapping = {}
    for name in set(new_ids) & set(old_ids):
        new_array, new_id = new_ids[name]
        old_array, old_id = old_ids[name]
        require(new_array == old_array, 'Allocator type-array owner changed: ' + name)
        mapping[old_id] = new_id
    for name in set(new_ids) ^ set(old_ids):
        require(name in exact_compiler or changed_jass_name(name, proof), 'Unexpected allocator added/removed: ' + name)
    maps = source_line_maps(source, baseline_source)
    compare_count, kept = 0, 0
    changed = []
    for name in set(current) | set(before):
        if name in exact_compiler:
            changed.append(name)
            continue
        if changed_jass_name(name, proof):
            changed.append(name)
            # Shared old allocators must retain allocator mechanics even when
            # their fields/methods are an approved changed source owner.
            if name not in set(new_ids) & set(old_ids):
                continue
        require(name in current and name in before, 'Unrelated JASS function added/removed: ' + name)
        new, old = current[name][0], before[name][0]
        new = diagnostic_view(new, maps)
        new = local_alpha_view(new, old)
        if name in new_ids:
            require(name in old_ids, 'Unproved allocator identity')
            new = ASSIGN.sub(lambda m: m[1] + str(old_ids[name][1]) + m[4] if int(m[3]) else m[0], new)
        now_tests, old_tests = list(TYPE_TEST.finditer(new)), list(TYPE_TEST.finditer(old))
        require(len(now_tests) == len(old_tests), 'Type comparison count changed: ' + name)
        spans = []
        for now, prior in zip(now_tests, old_tests):
            require(now[1] == prior[1], 'Type comparison operand/operator changed: ' + name)
            expected = mapping.get(int(prior[2]), int(prior[2]))
            require(int(now[2]) == expected, 'Unproved type comparison boundary changed: ' + name)
            spans.append((now.start(2), now.end(2), prior[2]))
            compare_count += 1
        for start, end, value_ in reversed(spans):
            new = new[:start] + value_ + new[end:]
        require(new == old, 'Unrelated/allocator JASS implementation changed: ' + name)
        kept += 1
    def globals_(text):
        return text.split('globals\n', 1)[1].split('endglobals', 1)[0].splitlines()
    a, b = globals_(script), globals_(baseline)
    changed_owners = {Path(p).stem for p in proof['changed_owners']}
    changed_classes = set(proof['changed_classes'])
    def owned(line):
        if not line or line.startswith('//'):
            return False
        declaration = re.fullmatch(r'\w+ (?:array )?(\w+)(?:\s*=.*)?', line)
        require(declaration is not None, 'Unsupported global declaration')
        name = declaration[1]
        # Source-backed named global/field owners; generated bare captures are
        # intentionally excluded until an exact source binding can be proved.
        return any(name.startswith(owner + '_') for owner in changed_owners | changed_classes)
    if combined_06:
        require(len(a) == 1372 and a == reviewed_jass_templates['global_declarations'],
            'Exact combined-06 reviewed global declaration table changed')
    else:
        require([line for line in a if not owned(line)] == [line for line in b if not owned(line)], 'Unrelated/generated global declarations changed')
    def shell(text):
        for fn in reversed(list(functions(text).values())):
            text = text[:fn.start()] + text[fn.end():]
        text = re.sub(r'globals\n.*?endglobals', 'globals\nendglobals', text, count=1, flags=re.S)
        return text
    a_shell, b_shell = shell(script), shell(baseline)
    if combined_06:
        a_shell = '\n'.join(line for line in a_shell.splitlines() if line.strip())
        b_shell = '\n'.join(line for line in b_shell.splitlines() if line.strip())
    require(a_shell == b_shell, 'JASS compiler/header/native/outside-function bytes changed')
    return {'preserved_functions': kept, 'approved_changed_functions': sorted(changed),
            'proved_type_comparisons': compare_count, 'allocator_identity_count': len(mapping),
            'math_aliases': math_evidence, 'exact_reviewed_compiler_adaptations': sorted(exact_compiler),
            'exact_reviewed_deletions': sorted(COMBINED_06_EXACT_DELETIONS) if combined_06 else [],
            'exact_reviewed_global_declarations': len(a) if combined_06 else 0}


class PureBossJassRuntime(BossJassRuntime):
    """Execute actual packaged helpers with recorded engine boundaries.

    The inherited interpreter is bounded and fail-closed. Current-match lookup,
    result/reward flags, mechanic timing, movement and loot planning execute the
    candidate JASS. Stubbed external hooks expose reentrancy at CLOSING.
    """
    def seed_record(self, wave=32, role=3, active=True):
        self.table[100] = 10
        self.lists[700] = [10]
        fields = [('TDEnemyMechanicRecord_enemy', 10, 100), ('TDEnemyMechanicRecord_state', 10, 20),
            ('TDEnemyMechanicRecord_matchEpoch', 10, self.globals.get('TDWaveFlowState_tdFlowMatchEpoch', 0)),
            ('TDEnemyMechanicState_active', 20, active), ('TDEnemyMechanicState_role', 20, role),
            ('TDEnemyMechanicState_lane', 20, 0), ('TDEnemyMechanicState_wave', 20, wave),
            ('TDEnemyMechanicState_originalBaseSpeed', 20, 250.0)]
        for name, index, value_ in fields:
            require(name in self.globals, 'Missing new packaged Boss state: ' + name)
            self.globals[name][index] = value_
        # Interface dispatch's typed runtime check is still executed.
        for owner, index in (('TDEnemyMechanicRecord', 10), ('TDEnemyMechanicState', 20)):
            alloc = allocations(self.script).get('alloc_' + owner)
            if alloc:
                self.globals[alloc[0]][index] = alloc[1]

    def __init__(self, script):
        super().__init__(script)
        self.now, self.hook_hold, self.hook_reenter = 0.0, True, False
        self.hook_events, self.starts, self.scheduled, self.moves = [], [], [], []
        self.ability_events, self.random_draws, self.items_created = [], [], []
        self.tables = {600: self.table, 610: {100: 0}, 620: {}, 630: {}}
        if 'TDSpawn_tdEnemyMatchEpochs' in self.globals:
            self.globals['TDSpawn_tdEnemyMatchEpochs'] = 610
        if 'TDBossDarkTideRuntime_tdDarkTideBossTokens' in self.globals:
            self.globals['TDBossDarkTideRuntime_tdDarkTideBossTokens'] = 620
        self.units[100]['userdata'] = 3200
        self.units[101]['userdata'] = 0
        self.units[102]['userdata'] = 3200
        self.units[100]['speed'] = 250.0
        self.units[101]['speed'] = 0.0
        self.enum_unit = None
        self.capture_start = False
        self.capture_lane_cleanup = False
        self.random_values = []
        self.capture_wave_production = False
        self.execute_lane_state = False
        self.spawn_requests, self.force_schedule_requests, self.leave_registrations = [], [], []
        self.transition_cycle_choices = []
        self.globals['EVENT_PLAYER_LEAVE'] = 'playerLeave'
        if 'ref_function_bridge_tdHandleLanePlayerLeaveEvent' in self.globals:
            require(script.count('set ref_function_bridge_tdHandleLanePlayerLeaveEvent = function bridge_tdHandleLanePlayerLeaveEvent') == 1,
                'Leave event code reference has no exact generated bridge binding')
            self.globals['ref_function_bridge_tdHandleLanePlayerLeaveEvent'] = 'bridge_tdHandleLanePlayerLeaveEvent'
        for name, fn in self.functions.items():
            # Optimized stdlib min/max need their actual initialized extrema.
            if name.startswith('init_') and fn[0] == [] and name in ('init_Real', 'init_TDWaveFlowState', 'init_TDBossTransitionHook', 'init_TDBossRewardRules', 'init_TDEnemyMechanicData'):
                self.invoke(name)

    def native(self, name, args):
        if self.execute_lane_state and name in ('tdIsLaneActive', 'tdIsLaneDefeated', 'tdIsLaneFinished', 'tdIsGameOver', 'tdIsLanePlayer'):
            return False, None
        if name == 'registerPlayerEvent':
            self.leave_registrations.append(tuple(args)); return True, None
        if name == 'tdSyncPlayerResources':
            return True, None
        if self.capture_wave_production:
            if name == 'tdSpawnWave':
                self.spawn_requests.append(tuple(args[:2])); return True, None
            if name == 'tdScheduleForcedNextWave':
                self.force_schedule_requests.append(args[0]); return True, None
        if name in ('R2I', 'real_toInt'): return True, int(args[0])
        if name in ('I2R', 'int_toReal'): return True, float(args[0])
        if name in ('I2S', 'int_toString'): return True, str(args[0])
        if name == 'IMaxBJ': return True, max(args[:2])
        if name == 'GetUnitUserData': return True, self.units.get(args[0], {}).get('userdata', 0)
        if name == 'SetUnitUserData': self.units[args[0]]['userdata'] = args[1]; return True, None
        if name in ('tdEnemyLaneId', 'tdEnemyWave', 'tdEnemyWasLeaked'):
            return False, None
        if name == 'getElapsedGameTime': return True, self.now
        if name == 'GetUnitDefaultMoveSpeed': return True, self.units.get(args[0], {}).get('speed', 0.0)
        if name == 'SetUnitMoveSpeed': self.moves.append(tuple(args[:2])); return True, None
        if name == 'tdPetEnemySpeedFactor': return True, self.units.get(args[0], {}).get('petSlow', 1.0)
        if name == 'GetEnumUnit': return True, self.enum_unit
        if name.startswith('dispatch_Table_Table_'):
            require(args[0] in self.tables, 'Unknown native table boundary')
            table = self.tables[args[0]]
            op = name.removeprefix('dispatch_Table_Table_')
            if op == 'hasInt': return True, args[1] in table
            if op == 'loadInt': return True, table.get(args[1], 0)
            if op == 'saveInt': table[args[1]] = args[2]; return True, None
            if op == 'removeInt': table.pop(args[1], None); return True, None
            if op == 'hasBoolean': return True, bool(table.get(args[1], False))
            if op == 'flush': table.clear(); return True, None
            raise ValueError('Unknown native table operation: ' + name)
        if name == 'dispatch_LinkedList_LinkedList_getDummy':
            require(args[0] in self.lists and not self.lists[args[0]], 'Empty collection dummy oracle requires an actually empty modeled list')
            return True, 0
        if name == 'dispatch_LinkedList_LinkedList_clear':
            require(args[0] in self.lists and not self.lists[args[0]], 'Empty collection clear oracle cannot discard records')
            return True, None
        if name == 'GetWorldBounds': return True, 'worldBounds'
        if name == 'group_enumUnitsInRect': self.groups[args[0]] = []; return True, None
        if name == 'ForGroup':
            require(not self.groups[args[0]], 'Empty-arena oracle cannot discard real enumerated units')
            return True, None
        if name == 'tdStartGlobalWave' and self.capture_start:
            self.starts.append(args[0]); return True, None
        if name in ('tdRefreshHud', 'DisplayTimedTextToPlayer'):
            return True, None
        if name == 'doAfter': self.scheduled.append((args[0], args[1])); return True, args[1]
        if name == 'tdPetIsWild': return True, self.units.get(args[0], {}).get('wild', False)
        if name in ('unit_addAbility', 'unit_removeAbility'):
            self.ability_events.append((name, *args[:2])); return True, True
        if name == 'GetRandomInt':
            self.random_draws.append(tuple(args[:2]))
            result = self.random_values.pop(0) if self.random_values else args[1]
            require(args[0] <= result <= args[1], 'Random oracle value out of native bounds')
            return True, result
        if name == 'ModuloInteger': return True, args[0] % args[1]
        return super().native(name, args)

    def execute_call(self, name, args):
        if name == 'cyc_tdResumeBossTransition':
            self.transition_cycle_choices.append(args[0])
        return super().execute_call(name, args)

    def invoke_transition_api(self, name, *args):
        if name in self.functions:
            return self.invoke(name, *args)
        require('cyc_tdResumeBossTransition' in self.functions and
            name in ('tdResumeBossTransition', 'tdFlowReleaseTransition'),
            'Unknown or missing compiled transition API lowering')
        if name == 'tdResumeBossTransition':
            require(len(args) == 1, 'Compiled resume argument mismatch')
            self.invoke('cyc_tdResumeBossTransition', 0, args[0], 'offline compiled hook harness', 0, 0)
        else:
            require(len(args) == 2, 'Compiled release argument mismatch')
            self.invoke('cyc_tdResumeBossTransition', 3, args[0], 'offline compiled hook harness', args[1], 0)
        return self.globals['tempReturn_boolean']

    def run_timer(self, callback):
        type_id = self.globals['CallbackSingle_typeId'][callback]
        owner = next((name for name, (array, ident) in allocations(self.script).items()
                      if array == 'CallbackSingle_typeId' and ident == type_id), None)
        require(owner is not None, 'Scheduled callback has no actual allocator owner')
        name = owner.removeprefix('alloc_CallbackSingle_')
        self.invoke('call_' + name, callback)


def verify_packaged_rule_matrix(script, baseline_script):
    current, prior = PureBossJassRuntime(script), BossJassRuntime(baseline_script)
    prior_native = prior.native
    def formal_native(name, args):
        if name in ('R2I', 'real_toInt'): return True, int(args[0])
        if name in ('I2R', 'int_toReal'): return True, float(args[0])
        return prior_native(name, args)
    prior.native = formal_native
    count = 0
    for wave in range(1, 33):
        total = current.invoke('tdWaveEnemyCount', wave)
        if wave in BOSS_WAVES:
            require(total == 1 and current.invoke('tdWaveNormalEnemyCount', wave) == 0 and
                    current.invoke('tdWaveEliteEnemyCount', wave) == 0 and current.invoke('tdWaveBossGuardEnemyCount', wave) == 0 and
                    current.invoke('tdWaveBossEnemyCount', wave) == 1, 'Pure Boss composition mismatch')
        else:
            for helper in ('tdWaveEnemyCount', 'tdWaveNormalEnemyCount', 'tdWaveEliteEnemyCount', 'tdWaveBossGuardEnemyCount', 'tdWaveBossEnemyCount', 'tdWaveSpawnInterval', 'tdWaveUnitId'):
                require(current.invoke(helper, wave) == prior.invoke(helper, wave), 'Ordinary-wave packaged invariant changed: ' + helper)
                count += 1
        for helper in ('tdWaveKillGold', 'tdWaveReward'):
            require(current.invoke(helper, wave) == prior.invoke(helper, wave), 'Existing wave economy changed: ' + helper)
            count += 1
    require(sum(current.invoke('tdWaveEnemyCount', w) for w in range(1, 33)) == 474, 'Match must contain 474 real enemies')
    require([current.invoke('tdBossKillCompensation', w) for w in BOSS_WAVES] == list(BOSS_GOLD) and sum(BOSS_GOLD) == 489, 'Exact fixed Boss compensation changed')
    for roll in range(-1, 102):
        require(current.invoke('tdBossBonusDropSucceeds', roll) is (1 <= roll <= 15), 'Independent bonus is not exactly 15/100')
        require(current.invoke('tdBossBallDropSucceeds', roll) is (1 <= roll <= 2), 'Ball compensation is not exactly 2/100')
        count += 2
    require([current.invoke('tdBossNormalDropAttempts', w) for w in BOSS_WAVES] == [10, 14, 16, 18], 'Compensation normal attempts changed')
    require([current.invoke('tdBossBallDropAttempts', w) for w in BOSS_WAVES] == [11, 15, 18, 0], 'Compensation ball attempts changed')
    for wave in range(1, 33):
        current.seed_record(wave)
        factor = {8: 1.0, 16: 1.0, 24: 0.68, 32: 0.58}.get(wave, 1.0)
        close(current.invoke('TDEnemyMechanicState_scaledSpellAmount', 20, 100.0), 100.0 * factor, 'Actual packaged Boss state resistance')
        count += 1
    return count


def verify_packaged_flow(script):
    scenarios = 0
    for wave, result in itertools.product(BOSS_WAVES, range(2, 6)):
        runtime = PureBossJassRuntime(script)
        runtime.invoke('tdResetWaveFlowState')
        epoch = runtime.invoke('tdFlowEpoch')
        generation = runtime.invoke('tdFlowBeginSpawn', 0)
        require(generation > 0 and runtime.invoke('tdFlowPrepareBoss', wave), 'Flow preparation cannot start')
        require(runtime.invoke('tdFlowSpawnCallbackValid', 0, epoch, generation), 'Preparation cancels legitimate old production')
        runtime.invoke('tdFlowEndSpawn', 0, generation)
        require(runtime.invoke('tdFlowStartBoss', wave) and not runtime.invoke('tdFlowStartBoss', wave), 'Duplicate Boss start succeeded')
        require(not runtime.invoke('tdFlowSpawnCallbackValid', 0, epoch, generation), 'Boss start failed to invalidate old spawn generation')
        require(runtime.invoke('tdFlowActivateBoss', 0, wave, 10.0), 'Registered Boss cannot activate')
        require(not runtime.invoke('tdFlowBossExpired', 0, wave, 99.999) and runtime.invoke('tdFlowBossExpired', 0, wave, 100.0), '90-second deadline boundary changed')
        require(runtime.invoke('tdFlowClaimBossResult', 0, wave, result), 'Terminal result cannot be claimed')
        require(not runtime.invoke('tdFlowClaimBossResult', 0, wave, 2), 'Terminal result claimed twice')
        for helper, args in (('tdFlowClaimBossReward', (0, wave, epoch)), ('tdFlowClaimBossLoot', (0, wave)), ('tdFlowClaimBossBallCompensation', (0, wave))):
            require(runtime.invoke(helper, *args) is (result == 2), 'Non-kill granted reward/loot/ball claim: ' + helper)
            require(not runtime.invoke(helper, *args), 'Reward/loot/ball claim repeated: ' + helper)
        runtime.invoke('tdResetWaveFlowState')
        require(runtime.invoke('tdFlowEpoch') > epoch and not runtime.invoke('tdFlowClaimBossReward', 0, wave, epoch), 'Reset failed to invalidate old Boss reward')
        scenarios += 1
    mode = verify_packaged_hook_mode(script)
    if mode['mode'] == 'pureBossNoHook':
        return scenarios + verify_packaged_no_hook_intermissions(script)
    return scenarios + verify_packaged_transition_harness(script)['cases']


def verify_packaged_hook_mode(script):
    """Distinguish the empty production extension from a real registered trial."""
    names = set(functions(script))
    apis = {'tdFlowRegisterTransitionHook', 'tdRegisterBossTransitionHook', 'tdResumeBossTransition'}
    if apis <= names:
        return {'mode': 'registeredHook', 'elided_apis': []}
    if {'tdFlowRegisterTransitionHook', 'tdRegisterBossTransitionHook', 'cyc_tdResumeBossTransition'} <= names:
        cycle = functions(script)['cyc_tdResumeBossTransition'][0]
        require(cycle.startswith('function cyc_tdResumeBossTransition takes integer funcChoice, integer transitionToken, string w__wurst_stackPos, integer transitionToken_1, integer reason returns nothing\n'),
            'Unknown transition cycle signature')
        for choice in (0, 1, 2, 3):
            require(cycle.count(('if ' if choice == 0 else 'elseif ') + 'funcChoice == ' + str(choice) + ' then') == 1,
                'Compiled transition cycle choice changed')
        for binding in ('TDTransitionRuntimeHarness_releaseCalls[transitionToken]',
                        'TDBossTransitionHook_typeId[transitionToken] == 0',
                        'TDWaveFlowState_tdFlowTransitionState = 2',
                        'when calling tdResumeBossTransition in TDBossTransitionRuntimeHarness',
                        'when calling onRelease in TDBossTransitionHook'):
            require(binding in cycle, 'Compiled transition cycle source binding missing: ' + binding)
        return {'mode': 'registeredHookCycle', 'elided_apis': [],
            'lowering': 'real cyclic JASS choices0 resume,1 concrete release,2 interface release dispatch,3 flow release; actual body is executed'}
    require(not apis & names, 'Partially elided transition registration/resume API')
    assignments = re.findall(r'^\s*set TDWaveFlowState_tdFlowHook = ([^\n]+)$', script, re.M)
    require(assignments == ['0', '0'], 'Empty production hook has a nonzero or unexpected assignment')
    ready = functions(script)['dispatch_TDBossTransitionHook_TDBossTransitionHook_onReady'][0]
    release = functions(script)['dispatch_TDBossTransitionHook_TDBossTransitionHook_onRelease'][0]
    require(ready == 'function dispatch_TDBossTransitionHook_TDBossTransitionHook_onReady takes integer this_1, integer completedWave, integer transitionToken returns boolean\n\treturn false\nendfunction',
        'Empty production onReady dispatcher gained behavior')
    require(release == 'function dispatch_TDBossTransitionHook_TDBossTransitionHook_onRelease takes integer this_1, integer transitionToken, integer reason returns nothing\nendfunction',
        'Empty production onRelease dispatcher gained behavior')
    return {'mode': 'pureBossNoHook', 'elided_apis': sorted(apis),
        'boundary': 'Registration/resume/real hook callbacks are verified in source/staging or a separate real compiled harness, never claimed as executed in this production map.'}


def verify_packaged_no_hook_intermissions(script):
    """Execute real Game intermission, timer closure and next-wave state spine.

    Enemy production and its forced-start timer are captured engine boundaries.
    The Game scheduling/epoch/state methods and allocator-bound closure execute.
    """
    cases = 0
    for wave in (8, 24):
        runtime = PureBossJassRuntime(script)
        runtime.execute_lane_state = True
        runtime.invoke('tdResetState')
        runtime.invoke('tdSetLaneActive', 0, True)
        runtime.globals['TDState_tdGlobalWave'] = wave
        runtime.invoke('tdSetResolvedWave', 0, wave)
        runtime.globals['TDWaveFlowState_tdFlowPhase'] = 2
        runtime.globals['TDWaveFlowState_tdFlowBossWave'] = wave
        runtime.capture_wave_production = True
        runtime.invoke('tdBeginBossIntermission', wave)
        require(len(runtime.scheduled) == 1 and runtime.scheduled[0][0] == 30.0,
            'No-hook Boss intermission must schedule exactly one ordinary 30-second timer')
        require(runtime.globals['TDState_tdGlobalWave'] == wave, 'No-hook intermission advanced before its timer')
        callback = runtime.scheduled[0][1]
        runtime.run_timer(callback)
        require(runtime.globals['TDState_tdGlobalWave'] == wave + 1 and runtime.globals['TDWaveFlowState_tdFlowPhase'] == 0 and
            not runtime.invoke('tdIsNextWaveQueued'), 'No-hook timer did not actually advance Game state to next wave')
        require(runtime.spawn_requests == [(0, wave + 1)] and runtime.force_schedule_requests == [wave + 1],
            'No-hook next-wave production requested wrong lane/wave or repeated')
        runtime.run_timer(callback)
        require(runtime.spawn_requests == [(0, wave + 1)], 'Repeated intermission callback advanced again')
        cases += 1
    return cases


def verify_packaged_transition_harness(script):
    """Execute the separately compiled real hook class, dispatch and Game APIs.

    No hook call is intercepted. Native clock/timer and empty-arena enumeration
    are modeled; next-wave enemy production is captured separately from Game.
    This is a NON-RELEASE fixture, never evidence of a production registered hook.
    """
    mode = verify_packaged_hook_mode(script)['mode']
    require(mode in ('registeredHook', 'registeredHookCycle'), 'Real compiled hook APIs missing')
    names = set(functions(script))
    required = {'new_TDTransitionRuntimeHarness', 'alloc_TDTransitionRuntimeHarness',
        'TDTransitionRuntimeHarness_onReady'}
    if mode == 'registeredHook': required.add('TDTransitionRuntimeHarness_onRelease')
    require(required <= names, 'Dedicated compiled hook fixture methods missing')
    owner_array, type_id = allocations(script)['alloc_TDTransitionRuntimeHarness']
    require(owner_array == 'TDBossTransitionHook_typeId', 'Harness allocator is not bound to the hook interface type array')
    records = []
    def fresh(wave, accept):
        runtime = PureBossJassRuntime(script)
        runtime.execute_lane_state = True
        runtime.capture_wave_production = True
        runtime.invoke('tdResetState')
        runtime.invoke('tdSetLaneActive', 0, True)
        runtime.invoke('tdSetResolvedWave', 0, wave)
        runtime.invoke('tdSetGlobalWave', wave)
        runtime.globals['TDWaveFlowState_tdFlowPhase'] = 2
        runtime.globals['TDWaveFlowState_tdFlowBossWave'] = wave
        hook = runtime.invoke('new_TDTransitionRuntimeHarness')
        require(runtime.globals[owner_array][hook] == type_id, 'Real hook allocator did not install its actual interface typeId')
        runtime.globals['TDTransitionRuntimeHarness_acceptHold'][hook] = accept
        runtime.globals['TDTransitionRuntimeHarness_reenterOnRelease'][hook] = True
        require(runtime.invoke('tdRegisterBossTransitionHook', hook), 'Real hook cannot register')
        other = runtime.invoke('new_TDTransitionRuntimeHarness')
        require(not runtime.invoke('tdRegisterBossTransitionHook', other), 'Another hook overwrote the registered owner')
        runtime.invoke('tdBeginBossIntermission', wave)
        require(runtime.globals['TDTransitionRuntimeHarness_readyCalls'][hook] == 1 and
            runtime.calls['dispatch_TDBossTransitionHook_TDBossTransitionHook_onReady'] == 1 and
            runtime.calls['TDTransitionRuntimeHarness_onReady'] == 1, 'Real onReady/dispatch did not execute exactly once')
        return runtime, hook
    def released(runtime, hook, reason):
        require(runtime.globals['TDTransitionRuntimeHarness_releaseCalls'][hook] == 1 and
            runtime.globals['TDTransitionRuntimeHarness_lastReason'][hook] == reason and
            not runtime.globals['TDTransitionRuntimeHarness_reentrantResumeSucceeded'][hook] and
            ((mode == 'registeredHookCycle' and runtime.transition_cycle_choices.count(1) == 1 and
                runtime.transition_cycle_choices.count(2) == 1) or
             (mode == 'registeredHook' and runtime.calls['dispatch_TDBossTransitionHook_TDBossTransitionHook_onRelease'] == 1 and
                runtime.calls['TDTransitionRuntimeHarness_onRelease'] == 1)),
            'Real release/reason/dispatch/reentrant-resume contract changed')
    for wave in (8, 24):
        for action in ('reject', 'resume', 'timeout', 'reset', 'last_lane_defeated'):
            runtime, hook = fresh(wave, action != 'reject')
            if action == 'reject':
                released(runtime, hook, 1)
                require(len(runtime.scheduled) == 1 and runtime.scheduled[0][0] == 30.0, 'Rejected hook did not use one ordinary 30-second wait')
                runtime.run_timer(runtime.scheduled[0][1])
            else:
                token = runtime.invoke('tdFlowHeldTransitionToken')
                require(token > 0 and len(runtime.scheduled) == 1 and runtime.scheduled[0][0] == 120.0,
                    'Accepted hold did not replace ordinary wait with one 120-second safety timer')
                require(not runtime.invoke_transition_api('tdResumeBossTransition', token + 1), 'Stale token resumed a held hook')
                require(not runtime.invoke('tdFlowCallTransitionReady', wave, token), 'Repeated ready callback succeeded')
                if action == 'resume':
                    require(runtime.invoke_transition_api('tdResumeBossTransition', token), 'Normal held resume failed')
                    released(runtime, hook, 1)
                    require(not runtime.invoke_transition_api('tdResumeBossTransition', token), 'Repeated resume succeeded')
                elif action == 'timeout':
                    runtime.run_timer(runtime.scheduled[0][1])
                    released(runtime, hook, 2)
                elif action == 'reset':
                    runtime.invoke('tdResetState')
                    released(runtime, hook, 3)
                    require(not runtime.invoke_transition_api('tdResumeBossTransition', token), 'Reset accepted old resume token')
                else:
                    runtime.lists[700].clear(); runtime.table.clear()
                    runtime.globals['TDBossDarkTideRuntime_tdDarkTideRecords'] = 710
                    runtime.lists[710] = []
                    runtime.globals['TDTowerEvolutionRuntime_tdEvolutionTowers'] = 720
                    runtime.lists[720] = []
                    runtime.invoke('tdSetLaneDefeated', 0, True)
                    runtime.invoke('tdHandleGameResolved')
                    released(runtime, hook, 3)
                    require(runtime.invoke('tdIsGameOver'), 'Last unfinished defeated lane did not end the Game')
            if action in ('reset', 'last_lane_defeated'):
                require(not runtime.spawn_requests and not runtime.force_schedule_requests, 'Abort/reset advanced the next wave')
            else:
                require(runtime.globals['TDState_tdGlobalWave'] == wave + 1 and runtime.spawn_requests == [(0, wave + 1)] and
                    runtime.force_schedule_requests == [wave + 1], 'Real held transition did not advance immediately exactly once')
            runtime.run_timer(runtime.scheduled[0][1])
            require(len(runtime.spawn_requests) == (0 if action in ('reset', 'last_lane_defeated') else 1),
                'Old/repeated transition timer advanced again')
            records.append({'wave': wave, 'action': action, 'ready_calls': 1,
                'release_reason': runtime.globals['TDTransitionRuntimeHarness_lastReason'][hook]})
    return {'mode': 'NON-RELEASE compiled same-source hook harness', 'cases': len(records), 'records': records,
        'allocator': {'owner': 'alloc_TDTransitionRuntimeHarness', 'type_array': owner_array, 'type_id': type_id},
        'hook_callbacks': 'actual interface dispatch and concrete methods executed; no hook callback stubs'}


def verify_packaged_leave_listener(script):
    runtime = PureBossJassRuntime(script)
    require(runtime.invoke('tdSetupLanePlayerLeaveWatcher'), 'First leave listener setup rejected')
    require(not runtime.invoke('tdSetupLanePlayerLeaveWatcher'), 'Duplicate startup installs another leave listener')
    runtime.invoke('tdResetState')
    require(not runtime.invoke('tdSetupLanePlayerLeaveWatcher'), 'Match reset re-registers lifetime leave listener')
    require(runtime.leave_registrations == [('playerLeave', 'bridge_tdHandleLanePlayerLeaveEvent')],
        'Leave listener registered wrong event/callback or more than once')
    return 3


def verify_packaged_mechanics(script):
    scenarios = 0
    eligibility = PureBossJassRuntime(script)
    for wave, role in itertools.product(range(-1, 35), range(-1, 5)):
        sprint = role == 1 and wave in (12, 20, 28)
        tracked = sprint or (role == 3 and wave in BOSS_WAVES)
        require(eligibility.invoke('tdEnemySprintEnabled', wave, role) is sprint,
            'Actual role-by-wave sprint eligibility changed')
        require(eligibility.invoke('tdEnemyMechanicTracked', wave, role) is tracked,
            'Actual role-by-wave mechanic registration eligibility changed')
        scenarios += 2
    for wave in BOSS_WAVES:
        runtime = PureBossJassRuntime(script)
        runtime.seed_record(wave)
        runtime.globals['TDEnemyMechanicState_bossBurstRunning'][20] = False
        runtime.globals['TDEnemyMechanicState_bossEnraged'][20] = False
        runtime.globals['TDEnemyMechanicState_warningCycle'][20] = 0
        runtime.globals['TDEnemyMechanicState_pulseCycle'][20] = 0
        if wave == 8:
            for age, event, speed in ((9.999, 0, 250.0), (10.0, 1, 250.0), (10.999, 0, 250.0), (11.0, 0, 325.0), (12.999, 0, 325.0), (13.0, 0, 250.0), (20.0, 1, 250.0), (21.0, 0, 325.0)):
                require(runtime.invoke('TDEnemyMechanicState_updateBoss', 20, age, 1.0) == event, 'Lifetime warning/burst event timing changed')
                close(runtime.invoke('TDEnemyMechanicState_baseSpeed', 20), speed, 'Native-composable Boss base movement')
                scenarios += 1
        elif wave == 24:
            for age, event in ((11.999, 0), (12.0, 1), (12.999, 0), (13.0, 2), (13.1, 0), (24.0, 1), (25.0, 2)):
                require(runtime.invoke('TDEnemyMechanicState_updateBoss', 20, age, 1.0) == event, 'Dark-tide warning/pulse/idempotence changed')
                scenarios += 1
        elif wave == 32:
            for hp, event, speed in ((.300001, 0, 250.0), (.30, 4, 287.5), (.20, 0, 287.5), (.60, 0, 287.5)):
                require(runtime.invoke('TDEnemyMechanicState_updateBoss', 20, 1.0, hp) == event, 'Enrage is not once at <=30%')
                close(runtime.invoke('TDEnemyMechanicState_baseSpeed', 20), speed, 'Enrage speed changed')
                scenarios += 1
        require(not runtime.invoke('TDEnemyMechanicState_beginSprint', 20, 2), 'Boss retained guard/waypoint sprint')
        runtime.invoke('TDEnemyMechanicState_deactivate', 20)
        require(runtime.invoke('TDEnemyMechanicState_updateBoss', 20, 100.0, .1) == 0, 'Retired Boss mechanic can fire')
    return scenarios


def validate_pure_boss_artifact(candidate, baseline, source, baseline_source, approved_source_owners, reviewed_jass_templates=None):
    current_source, formal_source = source_files(source), source_files(baseline_source)
    proof = verify_source_delta(current_source, formal_source, approved_source_owners)
    archive = verify_archive_delta(candidate, baseline)
    current_objects = {name: parse_objects(candidate.extract(name), extended) for name, extended in OBJECTS.items() if candidate.has(name)}
    formal_objects = {name: parse_objects(baseline.extract(name), extended) for name, extended in OBJECTS.items() if baseline.has(name)}
    objects = verify_object_delta(current_objects, formal_objects)
    icons = verify_icons(candidate, source)
    script, old_script = candidate.extract('war3map.j').decode(), baseline.extract('war3map.j').decode()
    jass = prove_jass_delta(script, old_script, current_source, formal_source, proof, reviewed_jass_templates)
    return {'source': proof, 'archive': archive, 'objects': objects, 'icons': icons, 'jass': jass,
        'packaged_native_engine_cases': verify_engine_and_accounting(script, PureBossJassRuntime,
            {8: 100.0, 16: 100.0, 24: 68.0, 32: 58.0}),
        'packaged_hook_mode': verify_packaged_hook_mode(script),
        'packaged_leave_listener_cases': verify_packaged_leave_listener(script),
        'packaged_rule_cases': verify_packaged_rule_matrix(script, old_script),
        'packaged_flow_cases': verify_packaged_flow(script),
        'packaged_mechanic_cases': verify_packaged_mechanics(script),
        'limits': ['Offline bounded execution and native call capture, not Warcraft gameplay.',
                   'Negative item attack-speed stacking, UI rendering and Boss balance remain unobserved.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate_map', nargs='?', type=Path)
    parser.add_argument('--baseline-map', type=Path)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--baseline-source', type=Path, required=True)
    parser.add_argument('--approved-source-owner', action='append', default=[])
    parser.add_argument('--source-only', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--reviewed-jass-templates', type=Path, help='Exact real-build template manifest after independent review; PENDING manifests are rejected')
    args = parser.parse_args()
    if args.source_only:
        require(args.candidate_map is None and args.baseline_map is None, 'Source-only cannot imply candidate-map validation')
        result = {'mode': 'source-only', 'source': verify_source_delta(source_files(args.source), source_files(args.baseline_source), args.approved_source_owner)}
    else:
        require(args.candidate_map is not None and args.baseline_map is not None, 'Final gate needs candidate and immutable formal baseline maps')
        result = validate_pure_boss_artifact(Mpq(args.candidate_map.read_bytes()), Mpq(args.baseline_map.read_bytes()), args.source, args.baseline_source, args.approved_source_owner, json.loads(args.reviewed_jass_templates.read_text(encoding='utf-8')) if args.reviewed_jass_templates else None)
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(serialized + '\n', encoding='utf-8')
    print(serialized)


if __name__ == '__main__':
    main()

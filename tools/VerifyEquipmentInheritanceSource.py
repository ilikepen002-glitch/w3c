#!/usr/bin/env python3
"""Finite current40 source inheritance gate; historical Boss gates stay unchanged.

Only the reviewed seven damage sites and two trial HP sites are allowed.
Manager core files stay byte-identical to formal009; five changed pet owners
have independently reviewed exact hashes. This is source evidence, not MPQ or
native execution evidence. The candidate cannot supply an approval manifest.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
from pathlib import Path
import re
import subprocess
from VerifyEquipmentAbilityArtifact import require

ROOT = Path(__file__).resolve().parents[1]
FORMAL = '009dae4dc2a27382477ff1ea624c6fd6a91b5a19'
FORMAL_TREE = '2960fc1a52b14fd671cd9dc4414f67a4e7e3494c'
DAMAGE_SITES = (
    ('items/TDEquipmentCombat.wurst', 'tdCaptureEquipmentAdditionalDamage', 'source.damageTarget(target, additional)'),
    ('items/TDEquipmentCombat.wurst', 'tdTickEquipmentDebuffs', 'source.damageTarget(target, tdEnemyMechanicScaleSpellDamage(target, amount))'),
    ('items/TDEquipmentSpecialRuntime.wurst', 'tdDealSpecialSpell', 'source.damageTarget(victim, tdEnemyMechanicScaleSpellDamage(victim, amount))'),
    ('pets/TDPetCombat.wurst', 'damage', 'host.damageTarget(target, amount)'),
    ('towers/TDTowerRuntime.wurst', 'tdPulseOrcBladestorm', 'tower.damageTarget(victim, tdEnemyMechanicScaleSpellDamage(victim, damagePerTick))'),
    ('towers/TDTowerRuntime.wurst', 'tdHandleGhoulCorpseExplosionDamage', 'source.damageTarget(victim, tdEnemyMechanicScaleSpellDamage(victim, tdGhoulCorpseExplosionDamageForBranch(tdTowerLevelForUnitTypeId(GetUnitTypeId(source)), tdTowerBranchForUnitTypeId(GetUnitTypeId(source)), tdTowerIsEvolved(source))))'),
    ('towers/TDTowerRuntime.wurst', 'tdDealArcherSplitArrowAttackDamage', 'source.damageTarget(target, amount, true, true, tdArcherSplitArrowNativeAttackType(), DAMAGE_TYPE_NORMAL, WEAPON_TYPE_WHOKNOWS)'),
)
HP_SITES = (
    ('trial/TDTrialRuntime.wurst', 'tdTrialCreateTarget', 'target.setLife(TD_TRIAL_TARGET_HP * 1.0)'),
    ('trial/TDTrialRuntime.wurst', 'tdTrialRefillBeforeDamage', 'target.setLife(TD_TRIAL_TARGET_HP * 1.0)'),
)
# Hashes are filled only from the reviewed, source-frozen current40 patch.
REVIEWED_PET_OWNERS = {
    'pets/TDPetCombat.wurst': '1324a18b84a107aa44e30b90b359b08913d886f1a2d9ac0895d55ede4e38c5be',
    'pets/TDPetEffectState.wurst': 'd16021e4e1a82dc427b989075ad5dd40eebb277686c1b7d240e1250a0a2af021',
    'pets/TDPetRules.wurst': 'c33263d7ce6eb3f6862ba320c6d4fda8740c370303b19ef948890f551f204b6b',
    'pets/TDPetState.wurst': 'ae4f163757cbc753555de04d9a7e75b5094a2ab3fce079916b6c769e7b3da669',
    'pets/TDPetWild.wurst': '586ee92260c5551cc94a1e5348ab4788106b821338d7bd0cca2e706763e2abd9',
}


# Exact top-level declarations also prevent relocation into a new overload.
SOURCE_DECLARATIONS = {
    ('items/TDEquipmentCombat.wurst', 'tdCaptureEquipmentAdditionalDamage'): 'function tdCaptureEquipmentAdditionalDamage()',
    ('items/TDEquipmentCombat.wurst', 'tdTickEquipmentDebuffs'): 'function tdTickEquipmentDebuffs()',
    ('items/TDEquipmentSpecialRuntime.wurst', 'tdDealSpecialSpell'): 'function tdDealSpecialSpell(unit source, unit victim, int lane, real amount, int damageId)',
    ('pets/TDPetCombat.wurst', 'damage'): 'function damage(TDPet pet, unit host, int generation, unit target, real amount)',
    ('towers/TDTowerRuntime.wurst', 'tdPulseOrcBladestorm'): 'function tdPulseOrcBladestorm(unit tower, tdTrialCombatContext context)',
    ('towers/TDTowerRuntime.wurst', 'tdHandleGhoulCorpseExplosionDamage'): 'function tdHandleGhoulCorpseExplosionDamage()',
    ('towers/TDTowerRuntime.wurst', 'tdDealArcherSplitArrowAttackDamage'): 'function tdDealArcherSplitArrowAttackDamage(unit source, unit target, real amount, tdTrialCombatContext context, int revision)',
    ('trial/TDTrialRuntime.wurst', 'tdTrialCreateTarget'): 'public function tdTrialCreateTarget(int lane, int slot, int token, int generation, real now) returns boolean',
    ('trial/TDTrialRuntime.wurst', 'tdTrialRefillBeforeDamage'): 'function tdTrialRefillBeforeDamage()',
}
TOKEN = re.compile(
    r'(?P<space>\s+)|(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)|'
    r"""(?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|"""
    r'(?P<identifier>[A-Za-z_]\w*)|'
    r'(?P<number>(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)|'
    r'(?P<operator>==|!=|<=|>=|\+=|-=|\*=|/=)|(?P<other>.)', re.S)
DAMAGE_CALLS = frozenset(('damageTarget', 'UnitDamageTarget'))
HP_CALLS = frozenset(('SetUnitState', 'SetWidgetLife', 'SetUnitLife', 'SetUnitMaxState',
                      'setLife', 'setHP', 'setMaxHP', 'abortCurrent',
                      'setNextDamageElement', 'setNextDamageType'))


def lexical_tokens(text):
    """Small lexical scan, retaining offsets and literal identity, never eval."""
    return [(match.group(), match.start(), match.lastgroup) for match in TOKEN.finditer(text)
            if match.lastgroup not in ('space', 'comment')]


def canonical(text):
    return ' '.join(value for value, _, _ in lexical_tokens(text))


def source_owners(text, relative):
    # Strings/comments cannot create a declaration. Retain newlines/indentation
    # so every call is assigned to its actual container, including class methods.
    sanitized = TOKEN.sub(lambda match: ''.join('\n' if char == '\n' else ' '
                          for char in match.group()) if match.lastgroup in ('string', 'comment')
                          else match.group(), text)
    result, owner, offset = {}, '<outside top-level function>', 0
    for line in sanitized.splitlines(keepends=True):
        code = line.strip()
        if code:
            declaration = re.match(r'^(?:(?:public|private|protected|override|static)\s+)*function\s+([\w.]+)', code)
            if declaration:
                name = declaration[1]
                expected = SOURCE_DECLARATIONS.get((relative, name))
                if not line[0].isspace() and expected is not None and canonical(code) == canonical(expected):
                    owner = name
                else:
                    owner = '<unapproved function: ' + name + '>'
            elif not line[0].isspace() or re.match(r'^(?:(?:public|private|protected|abstract|static)\s+)*(?:class|interface|module|init|ondestroy|construct)\b', code):
                owner = '<outside approved top-level function>'
        result[offset] = owner
        offset += len(line)
    return result


def inventory(root, names):
    result = Counter()
    for path in sorted((root / 'wurst').rglob('*.wurst')):
        if any(part in ('_tests', '_build', 'dependencies') for part in path.relative_to(root).parts):
            continue
        relative = path.relative_to(root / 'wurst').as_posix()
        text = path.read_text()
        tokens = lexical_tokens(text)
        owners = source_owners(text, relative)
        for index, (value, offset, kind) in enumerate(tokens):
            if kind != 'identifier' or value not in names or index + 1 == len(tokens) or tokens[index + 1][0] != '(':
                continue
            # This recognizes spaces, line breaks and comments between lexical
            # tokens. The complete balanced call still has to equal its oracle.
            depth, end = 0, index + 1
            while end < len(tokens):
                token = tokens[end][0]
                if token == '(':
                    depth += 1
                elif token == ')':
                    depth -= 1
                    if depth == 0:
                        break
                end += 1
            require(end < len(tokens), 'Unbalanced production call: ' + relative + ': ' + value)
            start = index - 2 if index >= 2 and tokens[index - 1][0] == '.' else index
            statement = ' '.join(token[0] for token in tokens[start:end + 1])
            line_start = text.rfind('\n', 0, offset) + 1
            result[relative, owners.get(line_start, '<unknown container>'), statement] += 1
    return result


def expected_inventory(sites):
    return Counter((relative, owner, canonical(call)) for relative, owner, call in sites)


def verify_damage_and_hp(root=ROOT):
    root = Path(root)
    damage = inventory(root, DAMAGE_CALLS)
    require(damage == expected_inventory(DAMAGE_SITES), 'current40 exact production damage inventory changed: ' + repr(damage))
    hp = inventory(root, HP_CALLS)
    require(hp == expected_inventory(HP_SITES), 'current40 forbidden HP/abort/type/element compensation: ' + repr(hp))
    return {'damage_sites': sum(damage.values()), 'trial_hp_sites': sum(hp.values())}


def verify_manager(root=ROOT):
    root = Path(root)
    git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT)
    require(git('rev-parse', FORMAL + '^{tree}').decode().strip() == FORMAL_TREE,
            'current40 formal009 fixed tree identity differs')
    paths = git('ls-tree', '-r', '--name-only', FORMAL, '--', 'wurst/pets').decode().splitlines()
    baseline = {name.removeprefix('wurst/'): git('show', FORMAL + ':' + name)
                for name in paths if name.endswith('.wurst') and '/_tests/' not in name}
    current = {p.relative_to(root / 'wurst').as_posix(): p.read_bytes()
               for p in (root / 'wurst/pets').rglob('*.wurst') if '_tests' not in p.parts}
    require(set(current) == set(baseline), 'current40 manager exact source owner inventory changed')
    changed = {name for name in current if current[name] != baseline[name]}
    require(changed == set(REVIEWED_PET_OWNERS), 'current40 manager changed owner set differs: ' + repr(changed))
    for name, expected in REVIEWED_PET_OWNERS.items():
        require(hashlib.sha256(current[name]).hexdigest() == expected,
                'current40 manager reviewed source hash differs: ' + name)
    return {'formal_commit': FORMAL, 'preserved_owners': len(current) - len(changed),
            'exact_reviewed_changed_owners': sorted(changed)}


def verify(root=ROOT):
    return {'damage_hp': verify_damage_and_hp(root), 'manager': verify_manager(root)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    args = parser.parse_args()
    print('PASS SOURCE current40:', verify(args.source_root))
    print('NOT TESTED: packaged JASS or native gameplay')

if __name__ == '__main__':
    main()

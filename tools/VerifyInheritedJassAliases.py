"""Prove exact math-overload identity before forming an inherited-check view.

Deleting obsolete UI can renumber the compiler's min/max overload identifiers.
This never rewrites an MPQ or accepts numeric/control-flow differences. Actual
behavior oracles still execute the original packaged script independently.
"""
import re
from VerifyDamageRankingJass import functions
from VerifyEquipmentAbilityArtifact import require

MATH_ALIAS = re.compile(r'(?:min|max)_2(?:_\d+)*$')


def inherited_script_view(script, baseline):
    current, before = functions(script), functions(baseline)
    mapping = {}
    for name, function in current.items():
        if not MATH_ALIAS.fullmatch(name):
            continue
        # Parameter names/types, return type and every body byte must agree.
        same = lambda other: (function[2], function[3], function[4]) == (other[2], other[3], other[4])
        if name in before and same(before[name]):
            continue
        matches = [old for old, candidate in before.items()
                   if MATH_ALIAS.fullmatch(old) and old.split('_')[0] == name.split('_')[0] and same(candidate)]
        require(len(matches) == 1, 'Math overload lacks one exact declaration/body identity: ' + name)
        target = matches[0]
        require(target not in current, 'Math alias rewrite would collide with a packaged function: ' + target)
        mapping[name] = target
    require(len(set(mapping.values())) == len(mapping), 'Math alias mapping is not injective')
    # Replace only proved identifier tokens, never numbers or quoted strings.
    view = re.sub(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*',
                  lambda match: match[0] if match[0].startswith('"') else mapping.get(match[0], match[0]), script)
    return view, mapping

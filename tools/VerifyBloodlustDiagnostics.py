"""Prove changed source-line locations before a read-only inherited-check view.

No diagnostic is discarded. Each pre-existing site is checked against the
unique old-to-new equal source line before replacing its line number.
"""
from difflib import SequenceMatcher
import re
from VerifyEquipmentAbilityArtifact import require
from VerifyDamageRankingJass import functions

DIAGNOSTIC = re.compile(r'"((?:when calling [^"\n]+ in |via function reference )([A-Za-z_]\w*), line )(\d+)"')


def source_line_maps(current, baseline):
    maps = {}
    require(set(current) == set(baseline), 'Diagnostic source package set changed')
    for package, old_text in baseline.items():
        old, new = old_text.splitlines(), current[package].splitlines()
        mapping = {}
        for block in SequenceMatcher(None, old, new, autojunk=False).get_matching_blocks():
            for offset in range(block.size):
                mapping[block.a + offset + 1] = block.b + offset + 1
        maps[package] = mapping
    return maps


def proved_diagnostic_view(script, baseline_script, current_sources, baseline_sources):
    current, before = functions(script), functions(baseline_script)
    maps = source_line_maps(current_sources, baseline_sources)
    chunks, cursor, changed = [], 0, []
    for name, fn in current.items():
        text = fn[0]
        if name in before:
            groups = {}
            for match in DIAGNOSTIC.finditer(before[name][0]):
                groups.setdefault(match[1], []).append(match)
            current_groups = {}
            for match in DIAGNOSTIC.finditer(text):
                current_groups.setdefault(match[1], []).append(match)
            replacements = []
            for prefix, old_sites in groups.items():
                sites = current_groups.get(prefix, [])
                require(len(sites) == len(old_sites), 'Existing diagnostic count changed: ' + name)
                for site, old in zip(sites, old_sites):
                    package, old_line = old[2], int(old[3])
                    if package in maps:
                        require(old_line in maps[package], 'Existing diagnostic source line is not unchanged: ' + name)
                        expected = maps[package][old_line]
                    else:
                        expected = old_line
                    require(int(site[3]) == expected, 'Diagnostic source-line provenance changed: ' + name)
                    replacements.append((site.start(3), site.end(3), str(old_line)))
                    if expected != old_line:
                        changed.append({'function': name, 'prefix': prefix, 'before': old_line, 'after': expected})
            for start, end, value in reversed(sorted(replacements)):
                text = text[:start] + value + text[end:]
        chunks.extend([script[cursor:fn.start()], text]); cursor = fn.end()
    chunks.append(script[cursor:])
    return ''.join(chunks), changed

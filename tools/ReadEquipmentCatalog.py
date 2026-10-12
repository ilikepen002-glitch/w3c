"""Read the authoritative Wurst equipment config; never maintain a second catalog."""
from dataclasses import dataclass
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Equipment:
    constant: str
    rawcode: str
    quality: int
    line: int
    next_id: str | None
    name: str
    primary: str
    primary_value: float
    secondary: str
    secondary_value: float
    aura: str
    aura_value: float
    aura_radius: float
    specialization: str


def catalog(root=ROOT):
    ids_source = (root / 'wurst/items/TDItemCatalogIds.wurst').read_text()
    ids = dict(re.findall(r"public constant int (TD_ITEM_\w+_ID) = '(.{4})'", ids_source))
    lines = {name: int(value) for name, value in re.findall(
        r'public constant int (TD_ITEM_LINE_\w+) = (\d+)', ids_source)}
    text = (root / 'wurst/items/TDItemCatalogConfig.wurst').read_text()
    pattern = (r'return tdEquipmentDefinition\((TD_ITEM_\w+_ID), (\d+), '
               r'(TD_ITEM_LINE_\w+), (TD_ITEM_\w+_ID|0), "([^"]+)", '
               r'TD_ITEM_EFFECT_(\w+), ([\d.]+), TD_ITEM_EFFECT_(\w+), ([\d.]+), '
               r'TD_ITEM_AURA_(\w+), ([\d.]+), ([\d.]+), TD_ITEM_SPECIAL_(\w+)\)')
    result = []
    for (constant, quality, line, next_id, name, primary, first, secondary,
         second, aura, value, radius, specialization) in re.findall(pattern, text):
        result.append(Equipment(constant, ids[constant], int(quality), lines[line],
                                None if next_id == '0' else ids[next_id], name,
                                primary, float(first), secondary, float(second),
                                aura, float(value), float(radius), specialization))
    if len(ids) != 40 or len(result) != 40 or len(lines) != 10:
        raise ValueError('Authoritative equipment config must contain 40 identities / 10 lines')
    return result


def icon_paths(root=ROOT):
    text = (root / 'wurst/items/TDItemData.wurst').read_text()
    text = text.split('public function tdItemIconPath', 1)[1].split(
        'public function tdItemPassiveAbilityRawcodes', 1)[0]
    result = {}
    line = None
    quality = None
    for row in text.splitlines():
        if match := re.fullmatch(r'\tif line == (\d+)', row):
            line = int(match[1])
        elif match := re.fullmatch(r'\t\tif quality == (\d+)', row):
            quality = int(match[1])
        elif match := re.fullmatch(r'\t\t\treturn "([^"]+)"', row):
            key = line, quality
            if key in result:
                raise ValueError('Duplicate equipment icon identity/rank')
            result[key] = match[1].replace('\\\\', '\\')
    if len(result) != 40:
        raise ValueError('Equipment icon dispatch must resolve all 40 identities')
    return result

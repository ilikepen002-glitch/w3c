"""In-memory future-contract fixtures, never edits source or packaged maps.

These corrections enable meaningful mutation tests while ExampleMap.w3x is
still the pre-release baseline. Actual-artifact positive tests stay uncorrected.
"""


def set_field(abilities, rawcode, field, value, level=0, column=None):
    fields = abilities[rawcode][1]
    matches = [key for key in fields if key[0] == field and key[1] == level
               and (column is None or key[2] == column)]
    if matches:
        key = matches[0]
        kind = fields[key][0]
    else:
        key = (field, level, 0 if column is None else column)
        kind = 3 if isinstance(value, str) else 0
    fields[key] = (kind, value)


def correct_release_contract(abilities, units):
    for rawcode in ('Phnt', 'Pmas', 'Pfor', 'Dsta'):
        abilities.pop(rawcode, None)
    set_field(abilities, 'Geqb', 'spb1', 'A119', 1, 1)
    set_field(abilities, 'Gupg', 'abpx', 1)
    set_field(abilities, 'Gupg', 'abpy', 1)
    for field, column in [('spb3', 3), ('spb4', 4)]:
        set_field(abilities, 'Geqb', field, 1, 1, column)
    name = '洗练 / 开栏 / 释放(C)'
    set_field(abilities, 'Pc06', 'anam', name)
    set_field(abilities, 'Pc06', 'atp1', name, 1)
    set_field(abilities, 'Pc06', 'aub1', '指定栏洗练并保留旧/替换新，开栏最高4；未上阵精灵可释放。', 1)
    for rawcode in ('Pcap', 'Pcol'):
        fields = abilities[rawcode][1]
        for key, (kind, text) in list(fields.items()):
            if key[0] in ('anam', 'atp1', 'aub1'):
                fields[key] = (kind, text.replace('猎杀、', '').replace('猎杀', '捕获'))
    for wave in range(1, 33):
        for species in range(1, 4):
            units[f'p{wave:02X}{species}']['ides'] = '本路保护60秒，仅可捕获。收藏中可释放未上阵精灵。'

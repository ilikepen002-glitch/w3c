#!/usr/bin/env python3
"""Verify native inventory constants at the actual MPQ root, not gameplay range."""
import argparse
import hashlib
from pathlib import Path
from GenerateTowerTerrainMask import Mpq

EXPECTED = b'[Misc]\nPickupItemRange=1200.0\nDropItemRange=1200.0\nGiveItemRange=1200.0\n'


def verify(path):
    data = Path(path).read_bytes()
    archive = Mpq(data)
    assert archive.has('war3mapMisc.txt'), 'Native gameplay constants missing at MPQ root'
    assert archive.extract('war3mapMisc.txt') == EXPECTED, 'Unexpected or overwritten gameplay constants'
    assert not archive.has(r'war3mapImported\war3mapMisc.txt'), 'Constants imported under ineffective asset prefix'
    return {'status': 'PASS', 'map_sha256': hashlib.sha256(data).hexdigest(),
            'member': 'war3mapMisc.txt', 'bytes': len(EXPECTED),
            'pickup_drop_give_range': 1200,
            'boundary': 'Packed native constants only; Warcraft 1.27a pickup/drop/give behavior not playtested'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map')
    print(verify(parser.parse_args().map))

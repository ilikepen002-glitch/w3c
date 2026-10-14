#!/usr/bin/env python3
"""Verify native inventory ranges and building Buff display at the MPQ root."""
import argparse
import configparser
import io
import hashlib
from pathlib import Path
from GenerateTowerTerrainMask import Mpq

EXPECTED = {
    'PickupItemRange': '1200.0',
    'DropItemRange': '1200.0',
    'GiveItemRange': '1200.0',
    'DisplayBuildingStatus': '1',
}


def verify_constants(data):
    # Strict/case-preserving parsing catches wrong section, typo and duplicates.
    # Compare the entire supported set so a display fix cannot reset other rules.
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str
    parser.read_file(io.StringIO(data.decode('utf-8-sig')))
    assert parser.sections() == ['Misc'] and not parser.defaults(), 'Unexpected gameplay constant sections'
    assert dict(parser['Misc']) == EXPECTED, 'Missing, changed or unexpected native gameplay constants'
    return dict(parser['Misc'])


def verify(path):
    data = Path(path).read_bytes()
    archive = Mpq(data)
    assert archive.has('war3mapMisc.txt'), 'Native gameplay constants missing at MPQ root'
    constants = archive.extract('war3mapMisc.txt')
    verify_constants(constants)
    assert not archive.has(r'war3mapImported\war3mapMisc.txt'), 'Constants imported under ineffective asset prefix'
    return {'status': 'PASS', 'map_sha256': hashlib.sha256(data).hexdigest(),
            'member': 'war3mapMisc.txt', 'bytes': len(constants),
            'pickup_drop_give_range': 1200, 'display_building_status': True,
            'boundary': 'Packed native constants only; Warcraft 1.27a inventory behavior and actual native Buff projection/display not playtested'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map')
    print(verify(parser.parse_args().map))

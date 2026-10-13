#!/usr/bin/env python3
"""Replay packaged music setup. Native audio is logged, not audibly simulated."""
import argparse
import hashlib
from pathlib import Path

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifyStartupArtifact import StartupRuntime
from VerifySemanticIconArtifact import import_records

PLAYLIST = ','.join('Sound\\Music\\mp3Music\\NightElf%d.mp3' % n for n in (1, 2, 3))
NATIVES = {'SetMusicVolume', 'SetMapMusic', 'PlayMusic'}
EXPECTED = [('SetMusicVolume', 45), ('SetMapMusic', PLAYLIST, False, 0), ('PlayMusic', PLAYLIST)]
AUDIO_SUFFIXES = ('.mp3', '.wav', '.ogg', '.flac', '.mid', '.midi', '.aiff', '.wma')


def music_events(runtime):
    return [event for event in runtime.events if event[0] in NATIVES]


def verify_script(script):
    runtime = StartupRuntime(script)
    require(not music_events(runtime), 'Music played before gameplay bootstrap')
    runtime.invoke('tdResetState')
    runtime.invoke('tdSetLaneActive', 0, True)
    runtime.invoke('tdFinalizeGameplayBootstrap')
    require(music_events(runtime) == EXPECTED, 'Actual bootstrap music sequence/paths/mix changed')
    camera = runtime.events.index(('tdLiftStartingCameraAgain',))
    require(camera < runtime.events.index(EXPECTED[0]), 'Music started before gameplay/camera bootstrap ended')
    require(len(runtime.scheduled) == 2, 'Music setup added scheduling beyond first wave and deferred HUD')
    for _ in range(3):
        runtime.invoke('tdFinalizeGameplayBootstrap')
        runtime.invoke('tdSetupBackgroundMusic')
    require(music_events(runtime) == EXPECTED, 'Repeated bootstrap/setup restarted or remixed music')
    runtime.invoke('tdResetState')
    runtime.invoke('tdSetupBackgroundMusic')
    require(music_events(runtime) == EXPECTED, 'Match reset restarted or remixed music')
    fresh = StartupRuntime(script)
    fresh.invoke('tdSetupBackgroundMusic')
    require(music_events(fresh) == EXPECTED, 'A fresh map inherited the prior music guard')
    require(not fresh.scheduled, 'Music-only setup allocated a scheduled callback')


def verify(map_path, expected_sha256=None):
    data = Path(map_path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    require(expected_sha256 is None or digest == expected_sha256.lower(), 'Candidate SHA256 mismatch')
    archive = Mpq(data)
    script = archive.extract('war3map.j').decode()
    verify_script(script)
    paths = import_records(archive.extract('war3map.imp'))
    paths += archive.extract('(listfile)').decode().splitlines()
    require(not any(path.lower().endswith(AUDIO_SUFFIXES) for path in paths),
            'Map contains imported audio instead of only native game assets')
    return {'sha256': digest, 'music': 'PASS', 'audio_imports': 0,
            'scope': 'Actual packaged JASS/native-call replay; no live audio or mute/slider test'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map')
    parser.add_argument('--sha256')
    args = parser.parse_args()
    print(verify(args.map, args.sha256))

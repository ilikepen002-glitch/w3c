"""Native-call replay only; does not claim in-game audio/mute verification."""
import unittest
from types import SimpleNamespace
from pathlib import Path
from test_elemental_pet_runtime_source import compile_body

ROOT = Path(__file__).resolve().parents[2]

def source(name):
    return (ROOT / 'wurst' / (name + '.wurst')).read_text()


class BackgroundMusicSourceTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.text = source('TDMusic')
        self.env = {
            'tdBackgroundMusicStarted': False,
            'Sounds': SimpleNamespace(nightElf1='elf1', nightElf2='elf2', nightElf3='elf3'),
            'SetMusicVolume': lambda volume: self.calls.append(('volume', volume)),
            'SetMapMusic': lambda *args: self.calls.append(('map', *args)),
            'PlayMusic': lambda playlist: self.calls.append(('play', playlist)),
        }
        compile_body(self.text, 'tdBackgroundMusicPlaylist', self.env)
        compile_body(self.text, 'tdBackgroundMusicVolume', self.env)
        self.setup = compile_body(self.text, 'tdSetupBackgroundMusic', self.env,
                                  ('tdBackgroundMusicStarted',))

    def test_playlist_starts_once_even_after_repeated_bootstrap(self):
        for _ in range(5):
            self.setup()
        self.assertEqual(self.calls, [('volume', 45), ('map', 'elf1,elf2,elf3', False, 0),
                                     ('play', 'elf1,elf2,elf3')])

    def test_music_has_no_forced_enable_sound_handles_or_periodic_work(self):
        code = '\n'.join(line.split('//')[0] for line in self.text.splitlines())
        for forbidden in ('EnableSound(', 'CreateSound(', 'StartSound(', 'CreateTimer(',
                          'TimerStart(', 'doPeriodically(', 'doAfter(', 'GetLocalPlayer('):
            self.assertNotIn(forbidden, code)
        # No reset/gameplay path can clear the map-lifetime guard.
        writes = [line.strip() for path in (ROOT / 'wurst').rglob('*.wurst')
                  for line in path.read_text().splitlines()
                  if 'tdBackgroundMusicStarted = false' in line]
        self.assertEqual(writes, ['boolean tdBackgroundMusicStarted = false'])

    def test_startup_runtime_records_only_native_audio_boundary(self):
        from VerifyStartupArtifact import StartupRuntime
        runtime = object.__new__(StartupRuntime)
        runtime.events = []
        for name, args in [('SetMusicVolume', [45]),
                           ('SetMapMusic', ['playlist', False, 0]),
                           ('PlayMusic', ['playlist'])]:
            self.assertEqual(runtime.native(name, args), (True, None))
        self.assertEqual(runtime.events, [('SetMusicVolume', 45),
                         ('SetMapMusic', 'playlist', False, 0), ('PlayMusic', 'playlist')])

    def test_only_startup_registers_music_after_gameplay_bootstrap(self):
        init = source('TDInit')
        self.assertEqual(init.count('tdSetupBackgroundMusic()'), 1)
        from VerifyPetManagerSource import function_body
        _, body = function_body(init, 'tdFinalizeGameplayBootstrap')
        self.assertLess(body.index('tdRunGameplayStartup()'), body.index('tdSetupBackgroundMusic()'))


if __name__ == '__main__':
    unittest.main()

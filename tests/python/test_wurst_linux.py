"""Focused Linux transaction failures. Fake processes are not real map/compiler evidence."""
import importlib.util
import json
from pathlib import Path
import shutil
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('wurst_linux', ROOT / 'tools/Run-WurstLinux.py')
linux = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linux)


def commit(root):
    subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=Tests', '-c', 'user.email=tests@example.invalid',
                    'commit', '-qm', 'fixture'], check=True)


class LinuxFailureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.root = self.home / 'repo'; self.root.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        for name, data in {'wurst.build': 'dependencies:\n- file:///E:/WurstToolchain/WurstStdlib2-source:pre1.29\nscriptMode: JASS\nwc3Patch: v1.28\n',
                           'wurst/Main.wurst': 'package Main\n', 'tests/wurst/Small.wurst': 'package Small\n',
                           'maps/ExampleMap.source.w3x': 'ORIGINAL-TEMPLATE', 'ExampleMap.w3x': 'OLD-OUTPUT',
                           'tools/VerifyActiveCooldownContract.py': '# explicit synthetic gate boundary\n',
                           '.gitignore': '/_build/\n/imports/ignored.bin\n',
                           'tools/compiler/legacy-jass-array-capacity.patch': 'compiler patch'}.items():
            p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(data)
        self.tools = self.home / 'tools'; self.tools.mkdir()
        (self.tools / 'wurstscript.jar').write_bytes(b'compiler')
        (self.tools / 'grill.jar').write_bytes(b'grill')
        self.jdk = self.home / 'jdk'; (self.jdk / 'bin').mkdir(parents=True)
        for name in ('java', 'javac'):
            p = self.jdk / 'bin' / name; p.write_text('test executable'); p.chmod(0o755)
        self.tool_lock = {'compilerSha256': linux.sha(self.tools / 'wurstscript.jar'),
                          'grillSha256': linux.sha(self.tools / 'grill.jar'),
                          'sourcePatchSha256': linux.sha(self.root / 'tools/compiler/legacy-jass-array-capacity.patch'),
                          'capacity': 8192, 'usableObjectIds': 8191}
        (self.root / 'tools/compiler/compiler-lock.json').write_text(json.dumps(self.tool_lock))
        self.stdlib = self.home / 'WurstStdlib2-source'; self.stdlib.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.stdlib)], check=True)
        (self.stdlib / 'common.j').write_text('constant integer JASS_MAX_ARRAY_SIZE = 8192\n')
        commit(self.stdlib)
        self.std_lock = {'fixedTree': linux.git(self.stdlib, 'rev-parse', 'HEAD^{tree}'),
                         'dependency': 'file:///E:/WurstToolchain/WurstStdlib2-source:pre1.29'}
        (self.root / 'tools/stdlib').mkdir()
        (self.root / 'tools/stdlib/lock.json').write_text(json.dumps(self.std_lock))
        commit(self.root)
        self.jdk_hashes = {n: linux.sha(self.jdk / n) for n in ('bin/java', 'bin/javac')}

    def verify(self):
        with patch.object(linux, 'JDK_FILES', self.jdk_hashes):
            linux.verify_tools(self.root, self.tools / 'wurstscript.jar', self.tools / 'grill.jar', self.jdk)

    def test_exact_fixture_preflight(self):
        self.verify(); linux.verify_stdlib(self.stdlib, self.std_lock)

    def test_three_wrong_sha_rejected_independently(self):
        for name in ('compilerSha256', 'grillSha256', 'sourcePatchSha256'):
            with self.subTest(name=name):
                wrong = dict(self.tool_lock); wrong[name] = '0' * 64
                (self.root / 'tools/compiler/compiler-lock.json').write_text(json.dumps(wrong))
                with self.assertRaisesRegex(RuntimeError, 'SHA256 mismatch'): self.verify()
        (self.root / 'tools/compiler/compiler-lock.json').write_text(json.dumps(self.tool_lock))

    def test_missing_tools_and_jdk_drift_rejected(self):
        for p in (self.tools / 'wurstscript.jar', self.tools / 'grill.jar', self.jdk / 'bin/java', self.jdk / 'bin/javac'):
            with self.subTest(path=p):
                data = p.read_bytes(); p.unlink()
                with self.assertRaises(RuntimeError): self.verify()
                p.write_bytes(data); p.chmod(0o755)
        (self.jdk / 'bin/java').write_text('different runtime')
        with self.assertRaisesRegex(RuntimeError, 'JDK27 SHA256'): self.verify()

    def test_configuration_capacity_and_executable_guards(self):
        for capacity, ids in ((32768, 8191), (8192, 8192)):
            bad = dict(self.tool_lock, capacity=capacity, usableObjectIds=ids)
            (self.root / 'tools/compiler/compiler-lock.json').write_text(json.dumps(bad))
            with self.assertRaisesRegex(RuntimeError, 'capacity lock'): self.verify()
        (self.root / 'tools/compiler/compiler-lock.json').write_text(json.dumps(self.tool_lock))
        original = (self.root / 'wurst.build').read_text()
        for text in (original.replace('JASS', 'LUA'), original.replace('v1.28', 'v1.32')):
            (self.root / 'wurst.build').write_text(text)
            with self.assertRaisesRegex(RuntimeError, 'JASS/v1.28'): self.verify()
        (self.root / 'wurst.build').write_text(original)
        (self.jdk / 'bin/java').chmod(0o644)
        with self.assertRaisesRegex(RuntimeError, 'executable'): self.verify()

    def test_wrong_dirty_untracked_and_ignored_stdlib_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'tree mismatch'):
            linux.verify_stdlib(self.stdlib, dict(self.std_lock, fixedTree='0' * 40))
        for name in ('common.j', 'added.wurst'):
            p = self.stdlib / name; old = p.read_bytes() if p.exists() else None
            p.write_text('changed')
            with self.assertRaisesRegex(RuntimeError, 'Dirty stdlib'): linux.verify_stdlib(self.stdlib, self.std_lock)
            p.write_bytes(old) if old is not None else p.unlink()
        (self.stdlib / '.gitignore').write_text('ignored.wurst\n'); commit(self.stdlib)
        self.std_lock['fixedTree'] = linux.git(self.stdlib, 'rev-parse', 'HEAD^{tree}')
        (self.stdlib / 'ignored.wurst').write_text('unknown source')
        with self.assertRaisesRegex(RuntimeError, 'Ignored untracked'): linux.verify_stdlib(self.stdlib, self.std_lock)

    def test_capacity_8192_exactly_once_not_32768_zero_or_duplicate(self):
        for text in ('constant integer JASS_MAX_ARRAY_SIZE = 32768\n',
                     'constant integer JASS_MAX_ARRAY_SIZE = 0\n',
                     'constant integer JASS_MAX_ARRAY_SIZE = 8192\n' * 2):
            (self.stdlib / 'common.j').write_text(text); commit(self.stdlib)
            lock = dict(self.std_lock, fixedTree=linux.git(self.stdlib, 'rev-parse', 'HEAD^{tree}'))
            with self.assertRaisesRegex(RuntimeError, '8192 exactly once'): linux.verify_stdlib(self.stdlib, lock)

    def test_links_files_parents_and_existing_staging_rejected(self):
        link = self.home / 'linked'; link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'Symlink'): linux.safe_path(link / 'wurst/Main.wurst', file=True)
        (self.root / 'wurst/_tests').mkdir()
        with self.assertRaisesRegex(RuntimeError, 'staging'): linux.inventory(self.root)
        (self.root / 'wurst/_tests').rmdir()
        (self.root / 'wurst/link.wurst').symlink_to(self.stdlib / 'common.j')
        with self.assertRaisesRegex(RuntimeError, 'Symlink'): linux.inventory(self.root)

    def test_snapshot_contains_actual_modifications_new_and_ignored_imports(self):
        (self.root / 'wurst/Main.wurst').write_text('package ActualModified\n')
        (self.root / 'wurst/New.wurst').write_text('package ActualNew\n')
        (self.root / 'imports').mkdir(); (self.root / 'imports/ignored.bin').write_bytes(b'actual ignored asset')
        recorded = linux.inventory(self.root); copy = self.home / 'snapshot'
        linux.snapshot(self.root, copy, recorded)
        for name in ('wurst/Main.wurst', 'wurst/New.wurst', 'imports/ignored.bin'):
            self.assertEqual((copy / name).read_bytes(), (self.root / name).read_bytes())

    def test_changed_snapshot_and_ambiguous_dependency_mapping_rejected(self):
        recorded = linux.inventory(self.root); (self.root / 'wurst/Main.wurst').write_text('changed')
        with self.assertRaisesRegex(RuntimeError, 'changed during snapshot'):
            linux.snapshot(self.root, self.home / 'copy', recorded)
        p = self.root / 'wurst.build'; original = p.read_text()
        mapped = linux.map_dependency(self.root, self.stdlib, self.std_lock)
        self.assertEqual(p.read_text(), original.replace(mapped['original'], mapped['temporary']))
        p.write_text(original + '- ' + self.std_lock['dependency'] + '\n')
        with self.assertRaisesRegex(RuntimeError, 'exactly the locked dependency'):
            linux.map_dependency(self.root, self.stdlib, self.std_lock)

    def test_shared_repository_lock_rejects_concurrent_transaction(self):
        with linux.serial_lock(self.root):
            with self.assertRaisesRegex(RuntimeError, 'holds this repository lock'):
                with linux.serial_lock(self.root): pass
        with linux.serial_lock(self.root): pass

    def test_test_stage_contains_only_wurst_and_is_cleaned(self):
        (self.root / 'tests/wurst/note.txt').write_text('not a test')
        linux.stage_tests(self.root)
        self.assertEqual([p.name for p in (self.root / 'wurst/_tests').iterdir()], ['Small.wurst'])
        with self.assertRaisesRegex(RuntimeError, 'Staging already exists'): linux.stage_tests(self.root)
        linux.clean_stage(self.root); self.assertFalse((self.root / 'wurst/_tests').exists())

    def test_native_check_input_comes_from_exact_real_template_without_modifying_it(self):
        shutil.copy2(ROOT / 'maps/ExampleMap.source.w3x', self.root / 'maps/ExampleMap.source.w3x')
        shutil.copy2(ROOT / 'tools/GenerateTowerTerrainMask.py', self.root / 'tools/GenerateTowerTerrainMask.py')
        before = linux.sha(self.root / 'maps/ExampleMap.source.w3x')
        evidence = linux.prepare_map_script(self.root)
        self.assertEqual(evidence['sourceTemplateSha256'], before)
        self.assertEqual(linux.sha(self.root / 'maps/ExampleMap.source.w3x'), before)
        script = (self.root / 'wurst/war3map.j').read_text()
        refs = set(re.findall(r'gg_rct_\w+', (ROOT / 'wurst/TDConfig.wurst').read_text()))
        self.assertEqual(len(refs), 14)
        for ref in refs:
            self.assertRegex(script, r'\brect\s+' + ref + r'\b')
        with self.assertRaisesRegex(RuntimeError, 'preexisting generated'):
            linux.prepare_map_script(self.root)

    def test_real_subprocess_is_stopped_on_interruption_before_stage_cleanup(self):
        runner = linux.Runner(self.home, os.environ.copy())
        timer = threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGINT))
        timer.start()
        try:
            with self.assertRaises(KeyboardInterrupt):
                runner.run([sys.executable, '-c', 'import time; time.sleep(30)'], self.home)
            self.assertIsNone(runner.child)
        finally:
            timer.cancel(); runner.stop()

    def test_real_derived_writer_stops_before_staging_cleanup_on_interrupt(self):
        stage = self.root / 'wurst/_tests'; stage.mkdir()
        writer = self.home / 'writer.log'; pidfile = self.home / 'derived.pid'
        child = ('import time; from pathlib import Path; p=Path(' + repr(str(writer)) + '); '
                 '\nwhile True:\n with p.open("a") as f: f.write("alive\\n"); f.flush()\n time.sleep(0.02)\n')
        parent = ('import subprocess,sys,time; from pathlib import Path; '
                  'p=subprocess.Popen([sys.executable,"-c",' + repr(child) + ']); '
                  'Path(' + repr(str(pidfile)) + ').write_text(str(p.pid)); time.sleep(30)')
        runner = linux.Runner(self.home, os.environ.copy())
        def interrupt_ready():
            deadline = time.monotonic() + 3
            while not writer.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            os.kill(os.getpid(), signal.SIGINT)
        timer = threading.Timer(0.1, interrupt_ready); timer.start()
        try:
            with self.assertRaises(KeyboardInterrupt):
                runner.run([sys.executable, '-c', parent], self.home)
            self.assertIsNone(runner.child)
            pid = int(pidfile.read_text())
            process = Path(f'/proc/{pid}/stat')
            self.assertTrue(not process.exists() or process.read_text().split()[2] == 'Z', 'Derived writer is still live')
            stopped = writer.read_bytes()
            self.assertTrue(stage.exists())
            linux.clean_stage(self.root)
            time.sleep(0.1)
            self.assertEqual(writer.read_bytes(), stopped)
            self.assertFalse(stage.exists())
        finally:
            timer.cancel(); runner.stop()

    def test_missing_multiple_stale_and_non_map_candidates_rejected(self):
        build = self.root / '_build'; build.mkdir(); inp = build / 'ExampleMap.input.w3x'; inp.write_text('input')
        with self.assertRaisesRegex(RuntimeError, 'exactly one'): linux.unique_candidate(self.root, inp)
        one = build / 'output.w3x'; one.write_text('new')
        self.assertEqual(linux.unique_candidate(self.root, inp), one)
        with self.assertRaisesRegex(RuntimeError, 'stale'): linux.unique_candidate(self.root, inp, [one])
        two = build / 'another.w3x'; two.write_text('new')
        with self.assertRaisesRegex(RuntimeError, 'exactly one'): linux.unique_candidate(self.root, inp)
        one.unlink(); two.unlink(); (build / 'output.w3x.bak').write_text('old')
        with self.assertRaisesRegex(RuntimeError, 'not a map output'): linux.unique_candidate(self.root, inp)

    def test_changed_candidate_failed_gate_and_failed_input_check_leave_output_unchanged(self):
        out = self.root / 'ExampleMap.w3x'; candidate = self.home / 'candidate.w3x'; candidate.write_text('candidate')
        expected = linux.sha(candidate); candidate.write_text('changed')
        with self.assertRaisesRegex(RuntimeError, 'changed after final gates'):
            linux.publish(candidate, out, expected, lambda temp: None)
        self.assertEqual(out.read_text(), 'OLD-OUTPUT')
        candidate.write_text('candidate')
        for message in ('final gate failed', 'input changed'):
            def fail(temp): raise RuntimeError(message)
            with self.assertRaises(RuntimeError): linux.publish(candidate, out, expected, fail)
            self.assertEqual(out.read_text(), 'OLD-OUTPUT')
        linux.publish(candidate, out, expected, lambda temp: None)
        self.assertEqual(out.read_text(), 'candidate')

    def test_source_change_during_copy_is_rejected_immediately_before_replace(self):
        out = self.root / 'ExampleMap.w3x'; candidate = self.home / 'candidate.w3x'
        candidate.write_text('candidate'); expected = linux.sha(candidate)
        recorded = linux.inventory(self.root)
        copy = shutil.copyfileobj
        def concurrent_edit(source, target):
            copy(source, target)
            (self.root / 'wurst/Main.wurst').write_text('concurrent user edit')
        def unchanged(temp):
            current = linux.inventory(self.root); current.pop(temp.relative_to(self.root).as_posix(), None)
            linux.require(current == recorded, 'Project input changed')
        with patch.object(linux.shutil, 'copyfileobj', concurrent_edit):
            with self.assertRaisesRegex(RuntimeError, 'Project input changed'):
                linux.publish(candidate, out, expected, unchanged)
        self.assertEqual(out.read_text(), 'OLD-OUTPUT')
        self.assertFalse(list(self.root.glob('.wurst-linux-map-*')))

    def test_only_exact_owned_temp_is_excluded_not_same_prefix_or_changed_output(self):
        output = self.root / 'ExampleMap.w3x'; before = linux.sha(output)
        recorded = linux.inventory(self.root)
        owned = self.root / '.wurst-linux-map-owned.w3x'; owned.write_text('verified temp')
        linux.verify_unchanged_inputs(self.root, recorded, output, before, owned)
        other = self.root / '.wurst-linux-map-other.w3x'; other.write_text('new user input')
        with self.assertRaisesRegex(RuntimeError, 'input changed'):
            linux.verify_unchanged_inputs(self.root, recorded, output, before, owned)
        other.unlink(); output.write_text('concurrent user map edit')
        with self.assertRaises(RuntimeError):
            linux.verify_unchanged_inputs(self.root, recorded, output, before, owned)
        self.assertEqual(output.read_text(), 'concurrent user map edit')

    def run_fake_transaction(self, mode, fail_at):
        calls = []
        def fake_run(runner, args, cwd):
            self.assertEqual(runner.env['XDG_CONFIG_HOME'], str(runner.tx / 'home/.config'))
            self.assertEqual(runner.env['HOME'], str(runner.tx / 'home'))
            self.assertIn(str(runner.tx / 'home'), runner.env['JAVA_TOOL_OPTIONS'])
            calls.append([str(a) for a in args])
            if 'clone' in args:
                Path(args[-1]).mkdir(parents=True)
            if 'install' in args:
                (cwd / '_build/dependencies/WurstStdlib2-source').mkdir(parents=True)
            if 'build' in args:
                (cwd / '_build/new.w3x').write_text('FAKE-MAP')
            if fail_at == 'mutate-active-map' and '--map' in args:
                Path(args[-1]).write_text('MUTATED-AFTER-LEGACY-GATE')
            if fail_at in args:
                raise KeyboardInterrupt() if fail_at == 'typecheck' else RuntimeError('injected failure')
        args = SimpleNamespace(root=self.root, tools=self.tools, jdk=self.jdk, stdlib=self.stdlib,
                               output=None, mode=mode, filter=None)
        with patch.object(linux, 'verify_tools'), patch.object(linux, 'verify_stdlib'), \
             patch.object(linux, 'prepare_map_script', return_value={'origin': 'explicit synthetic boundary'}), \
             patch.object(linux.Runner, 'run', fake_run), \
             patch.object(linux, 'python_map_gate', side_effect=RuntimeError('injected final gate')):
            with self.assertRaises((KeyboardInterrupt, RuntimeError)):
                linux.execute(args)
        tx = list((self.root / '_build').glob('linux-*'))[-1]
        self.assertFalse((tx / 'project/wurst/_tests').exists())
        self.assertFalse((self.root / 'wurst/_tests').exists())
        self.assertEqual((self.root / 'ExampleMap.w3x').read_text(), 'OLD-OUTPUT')
        self.assertEqual((self.root / 'maps/ExampleMap.source.w3x').read_text(), 'ORIGINAL-TEMPLATE')
        self.assertEqual(json.loads((tx / 'manifest.json').read_text())['status'], 'FAIL')
        return calls

    def test_interruption_stops_checks_and_cleans_staging(self):
        calls = self.run_fake_transaction('checks', 'typecheck')
        self.assertFalse(any('test' in c or 'build' in c for c in calls))

    def test_install_failure_does_not_start_compiler(self):
        calls = self.run_fake_transaction('checks', 'install')
        self.assertFalse(any('typecheck' in c or 'test' in c or 'build' in c for c in calls))

    def test_probe_failure_occurs_before_install_or_compile(self):
        calls = self.run_fake_transaction('checks', 'ProbeLinuxCompilerLaunch')
        self.assertFalse(any('install' in c or 'typecheck' in c or 'build' in c for c in calls))

    def test_real_gate_path_failure_has_no_root_publish(self):
        self.run_fake_transaction('build', 'never-in-args')

    def test_active_cooldown_source_failure_precedes_install_checks_or_build(self):
        for mode in ('checks', 'typecheck', 'test', 'build'):
            with self.subTest(mode=mode):
                calls = self.run_fake_transaction(mode, '--source-only')
                self.assertFalse(any('install' in c or 'typecheck' in c or 'test' in c or 'build' in c for c in calls))

    def test_active_cooldown_actual_candidate_gate_follows_legacy_and_precedes_publication(self):
        calls = self.run_fake_transaction('build', '--map')
        legacy = next(i for i, c in enumerate(calls) if 'VerifyLegacyJass' in c)
        active = next(i for i, c in enumerate(calls) if '--map' in c)
        patch_name = next(i for i, c in enumerate(calls) if 'PatchMapDisplayName' in c)
        self.assertLess(patch_name, legacy)
        self.assertLess(legacy, active)
        self.assertEqual(Path(calls[active][-1]).name, 'new.w3x')

    def test_active_cooldown_gate_cannot_mutate_candidate_or_publish_root(self):
        self.run_fake_transaction('build', 'mutate-active-map')


class JavaProbeTests(unittest.TestCase):
    """Synthetic API boundary only; the actual locked Grill is validated separately."""
    @classmethod
    def setUpClass(cls):
        cls.java = shutil.which('java'); cls.javac = shutil.which('javac')
        if not cls.java or not cls.javac:
            raise unittest.SkipTest('A complete JDK is required for synthetic launch-probe tests')

    def test_runtime_exact_identity_rejects_relative_missing_and_other_real_absolute_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'global').mkdir()
            (root / 'global/InstallationManager.java').write_text('''package global;
public final class InstallationManager {
 public static final InstallationManager INSTANCE = new InstallationManager();
 public String[] compilerLaunchCommand(String[] a) {
  return new String[]{System.getProperty("fake.runtime"), "-jar", System.getProperty("fake.compiler"), "-version"};
 }
}''')
            subprocess.run([self.javac, '-d', str(root), str(root / 'global/InstallationManager.java'),
                            str(ROOT / 'tools/compiler/ProbeLinuxCompilerLaunch.java')], check=True, capture_output=True)
            compiler = root / 'compiler.jar'; compiler.write_text('synthetic')
            expected = Path(self.java).resolve()
            other = root / 'other-java'; other.write_text('#!/bin/sh\nexit 0\n'); other.chmod(0o755)
            for runtime, success in ((str(expected), True), ('java', False), (str(root / 'missing'), False), (str(other), False)):
                with self.subTest(runtime=runtime):
                    result = subprocess.run([self.java, '-Dfake.runtime=' + runtime, '-Dfake.compiler=' + str(compiler),
                                             '-cp', str(root), 'ProbeLinuxCompilerLaunch', str(compiler), str(expected)], capture_output=True)
                    self.assertEqual(result.returncode == 0, success)


if __name__ == '__main__':
    unittest.main()

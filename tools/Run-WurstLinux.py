#!/usr/bin/env python3
"""Locked Linux checks/build; an isolated snapshot, never Windows deployment or gameplay.

Only the dependency URL in the disposable wurst.build is mapped. Project inputs,
Windows entrypoints and existing toolchain locks are never rewritten. Transactions
retain their logs/inventory; staged tests are removed even on failure/interruption.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
# Official OpenJDK 27+35-2325 Linux x64, archive SHA256
# 95fc37eb3a18a27a26d5904c2d89d52bace8dafa9a078ca27f4747fbc4bf070b.
JDK_FILES = {
    'bin/java': '47058b76c60929f12a1fe1e724f95dd9f4302624ed9fdd8d3cd26b578f0a4461',
    'bin/javac': 'e0669b1c8e2dde0114e6eed10ef356327646aacdc83755f51d5b7d7e0fd9ec87',
    'release': 'f63c9cd965a39ef30c7f559df1e62964d645ae2142c4685f65ea4cdd7caff791',
    'lib/modules': 'b53e41019fb96dfc783cdc43a4cea36b09aea9198efa8793c53cd01a6fcd8165',
    'lib/server/libjvm.so': '7eb93edb7f8c75241cef5e360c97a8b5e9917570f3e3b86ee809bab376d97902',
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def safe_path(path, *, file=False, missing=False):
    """Reject links in every user-supplied path component, including parents."""
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        require(not part.is_symlink(), f'Symlink is not an input/output path: {part}')
    if not missing:
        require(path.is_file() if file else path.is_dir(), f'Missing regular input: {path}')
    if path.exists():
        mode = path.stat().st_mode
        require(stat.S_ISREG(mode) if file else stat.S_ISDIR(mode), f'Unexpected path type: {path}')
    return path


def sha(path):
    safe_path(path, file=True)
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.STDOUT).decode().strip()


def inventory(root):
    safe_path(root)
    require(not (root / 'wurst/_tests').exists() and not (root / 'wurst/_tests').is_symlink(),
            'Existing Wurst test staging must be resolved before Linux checks/build')
    names = set(subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z',
                                        '--cached', '--others', '--exclude-standard']).decode().split('\0')) - {''}
    # Imported assets may deliberately be ignored; their actual bytes are inputs.
    imports = root / 'imports'
    if imports.exists() or imports.is_symlink():
        safe_path(imports)
        for current, dirs, files in os.walk(imports, followlinks=False):
            for name in dirs:
                safe_path(Path(current) / name)
            for name in files:
                names.add((Path(current) / name).relative_to(root).as_posix())
    result = {}
    for name in sorted(names):
        rel = Path(name)
        require(not rel.is_absolute() and '..' not in rel.parts and '.git' not in rel.parts,
                f'Invalid project input: {name}')
        if rel.parts[0] == '_build' or name in ('wurst.dependencies', 'wurst/war3map.j'):
            continue
        p = safe_path(root / rel, file=True)
        result[name] = {'sha256': sha(p), 'size': p.stat().st_size,
                        'mode': stat.S_IMODE(p.stat().st_mode)}
    return result


def snapshot(root, destination, recorded):
    require(not destination.exists(), 'Snapshot must start absent')
    destination.mkdir()
    for name, entry in recorded.items():
        source = safe_path(root / name, file=True)
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        require(sha(target) == entry['sha256'], f'Input changed during snapshot: {name}')
    require(inventory(root) == recorded, 'Project inputs changed during snapshot')


def verify_stdlib(path, lock):
    safe_path(path)
    safe_path(path / '.git')
    require(git(path, 'rev-parse', 'HEAD^{tree}') == lock['fixedTree'], 'Stdlib tree mismatch')
    require(not git(path, 'status', '--porcelain', '--untracked-files=all'), 'Dirty stdlib checkout')
    require(not git(path, 'ls-files', '--others', '--ignored', '--exclude-standard'), 'Ignored untracked stdlib inputs')
    common = safe_path(path / 'common.j', file=True).read_text()
    assignments = re.findall(r'^\s*constant\s+integer\s+JASS_MAX_ARRAY_SIZE\s*=\s*(\d+)\s*$', common, re.M)
    require(assignments == ['8192'], 'common.j must declare target capacity 8192 exactly once')


def verify_tools(root, compiler, grill, jdk):
    lock = json.loads((root / 'tools/compiler/compiler-lock.json').read_text())
    require(lock['capacity'] == 8192 and lock['usableObjectIds'] == 8191, 'Unexpected compiler capacity lock')
    for path, expected in ((compiler, lock['compilerSha256']), (grill, lock['grillSha256']),
                           (root / 'tools/compiler/legacy-jass-array-capacity.patch', lock['sourcePatchSha256'])):
        require(sha(path) == expected.lower(), f'Tool SHA256 mismatch: {path}')
    for name, expected in JDK_FILES.items():
        require(sha(jdk / name) == expected, f'Pinned Linux JDK27 SHA256 mismatch: {name}')
    require(os.access(jdk / 'bin/java', os.X_OK) and os.access(jdk / 'bin/javac', os.X_OK),
            'Pinned Java/javac must both be executable')
    config = (root / 'wurst.build').read_text()
    require(re.search(r'^scriptMode: JASS\s*$', config, re.M) and
            re.search(r'^wc3Patch: v1\.28\s*$', config, re.M), 'Locked compiler requires JASS/v1.28')


def map_dependency(root, stdlib, lock):
    p = root / 'wurst.build'
    text = p.read_text()
    old = '- ' + lock['dependency']
    require(text.splitlines().count(old) == 1 and text.count(lock['dependency']) == 1,
            'Expected exactly the locked dependency, without ambiguous mappings')
    mapped = '- ' + stdlib.as_uri() + ':pre1.29'
    p.write_text(text.replace(old, mapped, 1))
    return {'original': old, 'temporary': mapped}


def prepare_map_script(project):
    """Authentic editor JASS input for checks, extracted read-only inside the snapshot."""
    sys.path.insert(0, str(project / 'tools'))
    try:
        from GenerateTowerTerrainMask import Mpq
        template = project / 'maps/ExampleMap.source.w3x'
        before = sha(template)
        script = Mpq(template.read_bytes()).extract('war3map.j')
        require(script and b'function main takes nothing returns nothing' in script, 'Missing authentic template JASS')
        require(sha(template) == before, 'Read-only native input extraction changed source template')
        target = project / 'wurst/war3map.j'
        require(not target.exists(), 'Unexpected preexisting generated native input')
        target.write_bytes(script)
        return {'sourceTemplateSha256': before, 'scriptSha256': sha(target),
                'origin': 'read-only war3map.j from exact source template, not a stub or inherited built map'}
    finally:
        sys.path.pop(0)


@contextmanager
def serial_lock(root):
    common = Path(git(root, 'rev-parse', '--git-common-dir'))
    if not common.is_absolute():
        common = root / common
    key = hashlib.sha256(str(common.resolve()).encode()).hexdigest()
    # Worktrees of this repository share the same lock; never unlink a live inode.
    path = Path(tempfile.gettempdir()) / ('wurst-linux-' + key + '.lock')
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode) and os.fstat(fd).st_uid == os.getuid(), 'Unsafe build lock')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another checks/build transaction holds this repository lock')
        yield
    finally:
        os.close(fd)


class Runner:
    def __init__(self, tx, env):
        self.tx, self.env, self.child, self.sequence = tx, env, None, 0

    def stop(self):
        if self.child is not None:
            # Stop the complete process group, including Grill's compiler child.
            group = self.child.pid
            try:
                os.killpg(group, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(group, signal.SIGKILL)
                self.child.wait()
            deadline = time.monotonic() + 10
            while True:
                try:
                    os.killpg(group, 0)
                except ProcessLookupError:
                    break
                if time.monotonic() >= deadline:
                    try:
                        os.killpg(group, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    break
                time.sleep(0.05)
            self.child = None

    def run(self, args, cwd):
        self.sequence += 1
        log = self.tx / f'{self.sequence:02d}-{Path(str(args[0])).name}.log'
        print('RUN', json.dumps([str(a) for a in args]), flush=True)
        with log.open('w') as f:
            self.child = subprocess.Popen([str(a) for a in args], cwd=cwd, env=self.env,
                                          stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = self.child.wait()
                # A command must not leave a compiler child behind.
                self.stop()
            except BaseException:
                self.stop()
                raise
        print(log.read_text(errors='replace'), end='', flush=True)
        require(code == 0, f'Command failed ({code}); see {log}')


def stage_tests(project):
    stage = project / 'wurst/_tests'
    require(not stage.exists(), 'Staging already exists')
    stage.mkdir(parents=True)
    for source in sorted((project / 'tests/wurst').rglob('*.wurst')):
        safe_path(source, file=True)
        dest = stage / source.relative_to(project / 'tests/wurst')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)


def clean_stage(project):
    stage = project / 'wurst/_tests'
    if stage.exists() or stage.is_symlink():
        safe_path(stage)
        shutil.rmtree(stage)


def unique_candidate(project, input_map, before=()):
    require(not before, 'Build output directory contains a stale map')
    candidates = [p for p in (project / '_build').glob('*.w3x*') if p != input_map]
    require(len(candidates) == 1, 'Build must produce exactly one new candidate map')
    candidate = safe_path(candidates[0], file=True)
    require(candidate.name.lower().endswith('.w3x'), 'Candidate is not a map output')
    require(candidate.stat().st_size > 0, 'Empty candidate map')
    return candidate


def python_map_gate(project, candidate, expected_name):
    """Independent read-only real MPQ gate; historical closed-delta oracles are not relaxed."""
    sys.path.insert(0, str(project / 'tools'))
    try:
        from GenerateTowerTerrainMask import Mpq
        from VerifyMapBrandingArtifact import parse_info
        from VerifySemanticIconArtifact import parse_objects
        before = sha(candidate)
        archive = Mpq(candidate.read_bytes())
        script = archive.extract('war3map.j').decode('utf-8-sig')
        require('function main takes nothing returns nothing' in script, 'Missing packaged JASS main')
        require(not archive.has('war3map.lua'), 'Unexpected Lua artifact for JASS target')
        for name, extended in (('war3map.w3u', False), ('war3map.w3a', True), ('war3map.w3t', False),
                               ('war3map.w3b', False), ('war3map.w3d', True), ('war3map.w3h', False), ('war3map.w3q', True)):
            if archive.has(name):
                parse_objects(archive.extract(name), extended)
        fields, _ = parse_info(archive.extract('war3map.w3i'))
        require(fields['name'] == fields['title'] == expected_name, 'Final map/loading display name mismatch')
        require(fields['flags'] & 1 == 0, 'Final map still hides lobby preview')
        count = 0
        for p in sorted((project / 'imports').rglob('*')):
            if p.is_file():
                name = p.relative_to(project / 'imports').as_posix().replace('/', '\\')
                require(archive.extract(name) == p.read_bytes(), 'Packaged import differs: ' + name)
                count += 1
        require(count > 0, 'No packaged project imports checked')
        require(sha(candidate) == before, 'Python MPQ gate changed the candidate')
        return {'sha256': before, 'importsChecked': count, 'displayName': expected_name,
                'gate': 'real read-only Python MPQ/JASS/object tables/import bytes'}
    finally:
        sys.path.pop(0)


def publish(candidate, output, expected, unchanged):
    """All gates and the input-invariance callback must succeed before atomic replacement."""
    safe_path(output.parent)
    safe_path(output, file=True, missing=True)
    require(sha(candidate) == expected, 'Candidate changed after final gates')
    fd, name = tempfile.mkstemp(prefix='.wurst-linux-map-', suffix='.w3x', dir=output.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, 'wb') as target, candidate.open('rb') as source:
            shutil.copyfileobj(source, target)
            target.flush()
            os.fsync(target.fileno())
        require(sha(temp) == expected and sha(candidate) == expected, 'Candidate changed during publication')
        # All slow work (including the copy) precedes the callback's final source/output check.
        unchanged(temp)
        os.replace(temp, output)
    finally:
        temp.unlink(missing_ok=True)


def verify_unchanged_inputs(root, recorded, output, output_before, owned_temp=None):
    current = inventory(root)
    # Only publish's exact, already SHA-checked temporary file may be excluded.
    if owned_temp is not None and owned_temp.is_relative_to(root):
        current.pop(owned_temp.relative_to(root).as_posix(), None)
    require(current == recorded, 'Project input changed before publication')
    require((sha(output) if output.exists() else None) == output_before, 'Output changed during transaction')


def execute(args):
    root = safe_path(args.root)
    tools = safe_path(args.tools)
    jdk = safe_path(args.jdk)
    stdlib = safe_path(args.stdlib)
    output = safe_path(args.output or root / 'ExampleMap.w3x', file=True, missing=True)
    require(output.name.lower().endswith('.w3x'), 'Map output must have the .w3x extension')
    compiler, grill = tools / 'wurstscript.jar', tools / 'grill.jar'
    verify_tools(root, compiler, grill, jdk)
    lock = json.loads((root / 'tools/stdlib/lock.json').read_text())
    verify_stdlib(stdlib, lock)
    with serial_lock(root):
        recorded = inventory(root)
        # Never let an output option replace a source template or other tracked input.
        if output.is_relative_to(root) and output != root / 'ExampleMap.w3x':
            require(output.relative_to(root).as_posix() not in recorded, 'Output would overwrite a project source input')
        output_before = sha(output) if output.exists() else None
        txroot = safe_path(root / '_build', missing=True)
        txroot.mkdir(exist_ok=True)
        tx = Path(tempfile.mkdtemp(prefix='linux-', dir=txroot))
        print('TRANSACTION', tx, flush=True)
        report = {'status': 'RUNNING', 'transaction': str(tx), 'mode': args.mode,
                  'parentCommit': git(root, 'rev-parse', 'HEAD'), 'inputs': recorded,
                  'compilerSha256': sha(compiler), 'grillSha256': sha(grill),
                  'stdlibTree': lock['fixedTree'], 'jdkRuntime': '27+35-2325'}
        project = tx / 'project'
        env = os.environ.copy()
        for name in ('JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH'):
            env.pop(name, None)
        home = tx / 'home'; home.mkdir()
        temp = tx / 'tmp'; temp.mkdir()
        require(not any(c in str(home) + str(temp) for c in '\"\\\r\n'), 'Unsafe isolated JVM option path')
        env.update(HOME=str(home), JAVA_HOME=str(jdk), PATH=str(jdk / 'bin') + ':/usr/bin:/bin',
                   XDG_CONFIG_HOME=str(home / '.config'), XDG_CACHE_HOME=str(home / '.cache'),
                   XDG_DATA_HOME=str(home / '.local/share'),
                   WURST_STDLIB_SOURCE=str(stdlib),
                   PYTHONDONTWRITEBYTECODE='1',
                   JAVA_TOOL_OPTIONS=f'-Duser.home="{home}" -Djava.io.tmpdir="{temp}"')
        runner = Runner(tx, env)
        handlers = {s: signal.signal(s, signal.default_int_handler) for s in (signal.SIGINT, signal.SIGTERM)}
        try:
            snapshot(root, project, recorded)
            runner.run([sys.executable, safe_path(project / 'tools/VerifyActiveCooldownContract.py', file=True),
                        '--source-only'], project)
            report['activeCooldownSourceGate'] = 'PASS'
            report['nativeMapScript'] = prepare_map_script(project)
            local_stdlib = tx / 'stdlib-source/WurstStdlib2-source'
            local_stdlib.parent.mkdir()
            runner.run(['git', 'clone', '--no-hardlinks', '--branch', 'pre1.29', stdlib, local_stdlib], tx)
            verify_stdlib(local_stdlib, lock)
            report['dependencyMapping'] = map_dependency(project, local_stdlib, lock)
            install = tx / 'install'; (install / 'wurst-compiler').mkdir(parents=True)
            (install / 'grill-cli').mkdir()
            tool_compiler = install / 'wurst-compiler/wurstscript.jar'
            tool_grill = install / 'grill-cli/grill.jar'
            shutil.copy2(compiler, tool_compiler); shutil.copy2(grill, tool_grill)
            # The only allowed link is created here and points at the already verified JDK.
            (install / 'wurst-runtime').symlink_to(jdk, target_is_directory=True)
            classes = tx / 'classes'; classes.mkdir()
            java, javac = jdk / 'bin/java', jdk / 'bin/javac'
            compiler_cp = os.pathsep.join((str(classes), str(tool_compiler)))
            grill_cp = os.pathsep.join((str(classes), str(tool_grill)))
            sources = [project / 'tools/compiler' / (n + '.java') for n in
                       ('ProbeCompilerLaunch', 'ProbeLinuxCompilerLaunch', 'VerifyLegacyJass', 'VerifyLegacyJassTests')]
            sources.append(project / 'tools/PatchMapDisplayName.java')
            runner.run([java, '-version'], project); runner.run([javac, '-version'], project)
            runner.run([javac, '-cp', os.pathsep.join((str(tool_compiler), str(tool_grill))), '-d', classes, *sources], project)

            def probes():
                require((install / 'wurst-runtime').is_symlink() and
                        (install / 'wurst-runtime').resolve() == jdk, 'Unexpected isolated runtime link')
                require(sha(tool_compiler) == report['compilerSha256'] and sha(tool_grill) == report['grillSha256'],
                        'Isolated tool changed')
                for name, extra in (('ProbeCompilerLaunch', []), ('ProbeLinuxCompilerLaunch', [java])):
                    runner.run([java, '-Dwurst.install.dir=' + str(install), '-cp', grill_cp, name, tool_compiler, *extra], project)

            probes()  # Before install or any compiler invocation.
            runner.run([java, '-cp', compiler_cp, 'VerifyLegacyJassTests'], project)
            grill_cmd = [java, '-Dwurst.install.dir=' + str(install), '-Duser.home=' + str(home),
                         '-Dfile.encoding=UTF-8', '--enable-native-access=ALL-UNNAMED', '-jar', tool_grill]
            runner.run([*grill_cmd, 'install'], project)
            probes()
            dependency = project / '_build/dependencies/WurstStdlib2-source'
            verify_stdlib(dependency, lock)

            def compile_command(*command):
                verify_stdlib(local_stdlib, lock); verify_stdlib(dependency, lock)
                probes()
                runner.run([*grill_cmd, *command], project)
                probes()
                verify_stdlib(dependency, lock)

            def unchanged(owned_temp=None):
                verify_tools(root, compiler, grill, jdk)
                verify_stdlib(stdlib, lock); verify_stdlib(local_stdlib, lock); verify_stdlib(dependency, lock)
                probes()
                verify_unchanged_inputs(root, recorded, output, output_before, owned_temp)

            if args.mode != 'build':
                try:
                    stage_tests(project)
                    if args.mode in ('checks', 'typecheck'):
                        compile_command('typecheck', '--quiet')
                    if args.mode in ('checks', 'test'):
                        compile_command('test', *([args.filter] if args.filter else []), '--quiet')
                finally:
                    runner.stop()
                    clean_stage(project)
            else:
                require(not (project / 'wurst/_tests').exists(), 'Tests must not enter the production build')
                build = project / '_build'
                input_map = build / 'ExampleMap.input.w3x'
                require(not list(build.glob('*.w3x*')), 'Fresh build transaction contains a stale output')
                shutil.copy2(project / 'maps/ExampleMap.source.w3x', input_map)
                source_map_sha = sha(project / 'maps/ExampleMap.source.w3x')
                before = [p for p in build.glob('*.w3x*') if p != input_map]
                compile_command('build', input_map, '--quiet')
                candidate = unique_candidate(project, input_map, before)
                require(sha(project / 'maps/ExampleMap.source.w3x') == source_map_sha, 'Source map template changed')
                stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d-%H%M') + '-UTC+8'
                runner.run([java, '-cp', compiler_cp, 'PatchMapDisplayName', candidate, stamp], project)
                final_sha = sha(candidate)
                runner.run([java, '-cp', compiler_cp, 'VerifyLegacyJass', candidate], project)
                require(sha(candidate) == final_sha, 'Legacy JASS gate changed candidate')
                runner.run([sys.executable, project / 'tools/VerifyActiveCooldownContract.py', '--map', candidate], project)
                require(sha(candidate) == final_sha, 'Active cooldown gate changed candidate')
                report['activeCooldownArtifactGate'] = 'real MPQ/JASS PASS'
                runner.run([sys.executable, project / 'tools/VerifyPetStartupArtifact.py', candidate], project)
                runner.run([sys.executable, project / 'tools/VerifyStartupArtifact.py', candidate], project)
                require(sha(candidate) == final_sha, 'Startup gates changed candidate')
                report['startupArtifactGate'] = 'pet registration/routing and gameplay bootstrap PASS'
                report['artifact'] = python_map_gate(project, candidate, '契灵守卫战 ' + stamp)
                require(report['artifact']['sha256'] == final_sha, 'Candidate changed between gates')
                report['artifact']['candidate'] = str(candidate)
                if output.exists():
                    shutil.copy2(output, tx / 'previous-output.w3x')
                publish(candidate, output, final_sha, unchanged)
                report['artifact']['output'] = str(output)
            if args.mode != 'build':
                unchanged()
            report['status'] = 'PASS'
        except BaseException as error:
            report['status'] = 'FAIL'; report['error'] = repr(error)
            raise
        finally:
            runner.stop()
            if project.exists():
                clean_stage(project)
            for s, handler in handlers.items():
                signal.signal(s, handler)
            (tx / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            print(report['status'], 'manifest:', tx / 'manifest.json', flush=True)
        return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('checks', 'typecheck', 'test', 'build'), nargs='?', default='checks')
    p.add_argument('filter', nargs='?', help='Exact optional Grill test filter, only for test mode')
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--tools', type=Path, required=True, help='Directory containing the two exact locked jars')
    p.add_argument('--jdk', type=Path, required=True, help='Verified official OpenJDK 27+35-2325 Linux x64')
    p.add_argument('--stdlib', type=Path, required=True, help='Independent clean pre1.29 fixed-tree clone')
    p.add_argument('--output', type=Path, help='Only build: atomic map output; default root ExampleMap.w3x')
    args = p.parse_args()
    p.error('A test filter is only valid for test mode') if args.filter and args.mode != 'test' else None
    p.error('--output is only valid for build mode') if args.output and args.mode != 'build' else None
    try:
        execute(args)
    except (RuntimeError, OSError, subprocess.CalledProcessError, KeyboardInterrupt) as error:
        print('FAIL:', error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Compare explicit baseline/candidate method results without laundering failures.

Both runs must use identical final Python verifier/test inputs and selections.
Exit 0 means comparable with no new failures/coverage loss, never full-suite PASS.
Exit 1 means comparable with new failures. Exit 2 means incomparable, invalid,
or newly incomplete coverage. Existing failures remain visible in the output.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('python_checks_comparison_runner', ROOT / 'tools/Run-PythonChecks.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

OUTCOMES = {'PASS', 'FAIL', 'ERROR', 'SKIP', 'EXPECTED_FAILURE', 'UNEXPECTED_SUCCESS',
            'NOT_COVERED', 'FIXTURE_ERROR', 'FIXTURE_SKIP', 'NOT_RUN', 'RUNNING'}
BAD = {'FAIL', 'ERROR', 'UNEXPECTED_SUCCESS', 'FIXTURE_ERROR'}
UNCOVERED = {'SKIP', 'NOT_COVERED', 'FIXTURE_SKIP', 'NOT_RUN', 'RUNNING'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_report(report):
    require(isinstance(report, dict) and report.get('schema') == 'python-check-results-v1', 'Unsupported result schema')
    require(report.get('terminal') is True, 'Result has no confirmed terminal state')
    require(type(report.get('exit_code')) is int and report['exit_code'] in (0, 1, 2), 'Invalid terminal exit code')
    statuses = {'FAILED': {1}, 'PASSED_SELECTED': {0}, 'INCOMPLETE': {2}, 'INPUT_ERROR': {2}, 'LISTED': {0, 2}}
    require(report.get('status') in statuses and report['exit_code'] in statuses[report['status']], 'Terminal status/exit code mismatch')
    manifest = report.get('verification_manifest')
    require(isinstance(manifest, dict) and 'tools/Run-PythonChecks.py' in manifest, 'Missing final runner/verifier/test manifest')
    require(all(isinstance(key, str) and isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value)
                for key, value in manifest.items()), 'Invalid verification manifest digest')
    require(isinstance(report.get('methods'), list), 'Missing method results')
    rows = {}
    for row in report['methods']:
        require(isinstance(row, dict) and isinstance(row.get('id'), str) and row['id'] not in rows, 'Duplicate or invalid method result')
        require(row.get('outcome') in OUTCOMES and row.get('group') in ('source', 'regression', 'map', 'unclassified'), 'Invalid method outcome/group')
        require(isinstance(row.get('exceptions'), list) and isinstance(row.get('subtests'), list), 'Missing method exception/subtest details')
        require(type(row.get('executed')) is bool, 'Missing method execution flag')
        require(all(isinstance(error, dict) and all(isinstance(error.get(key), str) for key in ('type', 'message', 'traceback'))
                    for error in row['exceptions']), 'Missing exact exception text')
        require(row['outcome'] not in ('FAIL', 'ERROR', 'EXPECTED_FAILURE', 'FIXTURE_ERROR') or row['exceptions'], 'Missing failure/exception detail')
        require(all(isinstance(event, dict) and isinstance(event.get('id'), str) and event.get('outcome') in OUTCOMES
                    for event in row['subtests']), 'Invalid subtest result')
        rows[row['id']] = row
    selection = report.get('selection', {})
    require(isinstance(selection.get('requested'), dict) and isinstance(selection.get('methods'), list), 'Missing explicit selection')
    chosen = selection['methods']
    require(all(isinstance(row, dict) and isinstance(row.get('id'), str) and isinstance(row.get('group'), str) for row in chosen), 'Invalid selected method identity')
    require(len(chosen) == len(rows) and len({row['id'] for row in chosen}) == len(chosen), 'Selection/method count mismatch')
    require({row['id']: row['group'] for row in chosen} == {key: row['group'] for key, row in rows.items()}, 'Selection/method identity or group mismatch')
    summary = report.get('summary', {})
    require(isinstance(summary, dict) and summary.get('selected') == len(rows), 'Summary/selection count mismatch')
    require(all(type(summary.get(key)) is int and summary[key] >= 0 for key in
                ('selected', 'run', 'passed', 'failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes', 'not_covered')),
            'Invalid or missing terminal summary counters')
    require(summary['run'] == sum(row['executed'] for row in rows.values()), 'Summary/method execution count mismatch')
    require(summary['passed'] == sum(row['outcome'] == 'PASS' for row in rows.values()), 'Summary/method pass count mismatch')
    require(summary.get('not_covered') == sum(row['outcome'] == 'NOT_COVERED' for row in rows.values()), 'Summary/uncovered method count mismatch')
    require(summary.get('map_selected') == sum(row['group'] == 'map' for row in rows.values()) and
            summary.get('map_passed') == sum(row['group'] == 'map' and row['outcome'] == 'PASS' for row in rows.values()),
            'Summary/map method count mismatch')
    require(report['status'] != 'PASSED_SELECTED' or not (summary['failures'] or summary['errors'] or summary['unexpected_successes']), 'Failed counters contradict successful terminal status')
    require(isinstance(report.get('python_version'), str), 'Missing Python interpreter identity')
    require(isinstance(report.get('fixtures'), list) and isinstance(report.get('issues'), list), 'Missing fixture/run issues')
    require(all(isinstance(issue, str) for issue in report['issues']), 'Invalid run issue text')
    require(isinstance(report.get('discovery_errors'), list) and all(isinstance(event, dict) and
            all(isinstance(event.get(key), str) for key in ('module', 'type', 'message', 'traceback'))
            for event in report['discovery_errors']), 'Invalid discovery exception details')
    require(all(isinstance(event, dict) and isinstance(event.get('id'), str) and event.get('outcome') in OUTCOMES
                for event in report['fixtures']), 'Invalid fixture result')
    require(all(event['outcome'] not in BAD or isinstance(event.get('exception'), dict) and
                all(isinstance(event['exception'].get(key), str) for key in ('type', 'message', 'traceback'))
                for event in report['fixtures']), 'Missing exact fixture exception text')
    return rows


def manifest_delta(before, after):
    return dict(added=sorted(after.keys() - before.keys()), deleted=sorted(before.keys() - after.keys()),
                changed=[dict(path=key, baseline=before[key], candidate=after[key])
                         for key in sorted(before.keys() & after.keys()) if before[key] != after[key]])


def method_signature(row):
    return {key: row.get(key) for key in ('outcome', 'reason', 'exceptions', 'subtests', 'executed')}


def compare_reports(baseline, candidate, current_manifest):
    before, after = validate_report(baseline), validate_report(candidate)
    reasons = []
    if baseline.get('run_label') != 'baseline' or candidate.get('run_label') != 'candidate':
        reasons.append('Explicit baseline and candidate run labels are required')
    for label, report in (('baseline', baseline), ('candidate', candidate)):
        artifact = report.get('artifact', {})
        if not artifact.get('path') or not re.fullmatch('[0-9a-f]{64}', artifact.get('sha256') or ''):
            reasons.append(label + ' lacks an explicit hashed artifact input')
        if report.get('status') in ('INPUT_ERROR', 'LISTED', 'RUNNING') or any(row['outcome'] in ('NOT_RUN', 'RUNNING') for row in report['methods']):
            reasons.append(label + ' did not establish every selected method outcome')
        if 'verification_manifest_after' in report:
            reasons.append(label + ' verifier/test inputs changed while running')
    source_delta = manifest_delta(baseline['verification_manifest'], candidate['verification_manifest'])
    if any(source_delta.values()):
        reasons.append('Final runner/verifier/test SHA manifests differ')
    current_delta = manifest_delta(candidate['verification_manifest'], current_manifest)
    if any(current_delta.values()):
        reasons.append('Recorded inputs do not match the final on-disk runner/verifier/tests')
    if baseline.get('python_version') != candidate.get('python_version'):
        reasons.append('Python interpreter versions differ')
    if baseline.get('auxiliary_inputs', {}) != candidate.get('auxiliary_inputs', {}):
        reasons.append('Declared additional artifact/evidence inputs differ')
    added, deleted = sorted(after.keys() - before.keys()), sorted(before.keys() - after.keys())
    groups = [dict(id=key, baseline=before[key]['group'], candidate=after[key]['group'])
              for key in sorted(before.keys() & after.keys()) if before[key]['group'] != after[key]['group']]
    if baseline['selection']['requested'] != candidate['selection']['requested'] or added or deleted or groups:
        reasons.append('Requested/resolved method selection or classification differs')
    changed, new_failures, persistent, resolved, coverage_loss = [], [], [], [], []
    for key in sorted(before.keys() & after.keys()):
        one, two = before[key], after[key]
        if method_signature(one) != method_signature(two):
            changed.append(dict(id=key, baseline=method_signature(one), candidate=method_signature(two)))
        if two['outcome'] in BAD:
            (persistent if one['outcome'] in BAD and method_signature(one) == method_signature(two) else new_failures).append(key)
        if one['outcome'] in BAD and two['outcome'] == 'PASS':
            resolved.append(key)
        if two['outcome'] in UNCOVERED and (one['outcome'] not in UNCOVERED or method_signature(one) != method_signature(two)):
            coverage_loss.append(key)
        old_skips = [event for event in one['subtests'] if event['outcome'] == 'SKIP']
        if any(event not in old_skips for event in two['subtests'] if event['outcome'] == 'SKIP') and key not in coverage_loss:
            coverage_loss.append(key)
    new_failures.extend(key for key in added if after[key]['outcome'] in BAD)
    coverage_loss.extend(key for key in added if after[key]['outcome'] in UNCOVERED)
    new_fixture_errors = [event for event in candidate['fixtures'] if event['outcome'] in BAD and event not in baseline['fixtures']]
    new_issues = [issue for issue in candidate['issues'] if issue not in baseline['issues']]
    new_discovery_errors = [event for event in candidate.get('discovery_errors', []) if event not in baseline.get('discovery_errors', [])]
    comparable = not reasons
    exit_code = 2 if reasons or coverage_loss else 1 if new_failures or new_fixture_errors or new_issues or new_discovery_errors else 0
    status = 'INCOMPARABLE' if reasons else 'COMPARABLE_WITH_COVERAGE_LOSS' if coverage_loss else 'COMPARABLE_WITH_NEW_FAILURES' if exit_code else 'COMPARABLE_NO_NEW_FAILURES'
    return dict(schema='python-check-comparison-v1', status=status, comparable=comparable, exit_code=exit_code,
                reasons=reasons, source_manifest_delta=source_delta, final_disk_manifest_delta=current_delta,
                added_methods=added, deleted_methods=deleted, changed_groups=groups, changed_methods=changed,
                new_failures=new_failures, persistent_failures=persistent, resolved_failures=resolved,
                coverage_loss=coverage_loss, new_fixture_errors=new_fixture_errors, new_run_issues=new_issues,
                new_discovery_errors=new_discovery_errors,
                baseline=dict(artifact=baseline['artifact'], exit_code=baseline['exit_code'], status=baseline.get('status'), summary=baseline['summary']),
                candidate=dict(artifact=candidate['artifact'], exit_code=candidate['exit_code'], status=candidate.get('status'), summary=candidate['summary']),
                same_artifact=baseline['artifact'].get('sha256') == candidate['artifact'].get('sha256'),
                claim='Method comparison only; existing failures and uncovered checks remain failures/uncovered. No build or gameplay acceptance.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True, help='terminal --run-label baseline results JSON')
    parser.add_argument('--candidate', type=Path, required=True, help='terminal --run-label candidate results JSON')
    parser.add_argument('--output-json', type=Path)
    args = parser.parse_args(argv)
    try:
        require(not args.output_json or args.output_json.resolve() not in (args.baseline.resolve(), args.candidate.resolve()), 'Comparison output must not overwrite input reports')
        baseline, candidate = (json.loads(path.read_text()) for path in (args.baseline, args.candidate))
        result = compare_reports(baseline, candidate, runner.verification_manifest())
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = dict(schema='python-check-comparison-v1', status='INVALID_REPORT', comparable=False, exit_code=2, reasons=[str(error)])
    if args.output_json:
        try:
            runner.write_results_json(args.output_json, result)
        except (OSError, ValueError) as error:
            print('COMPARISON OUTPUT ERROR: ' + str(error), flush=True)
            return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())

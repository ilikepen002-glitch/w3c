"""Read-only audit of explicit Y3 resource IDs against saved dependency files.

This never edits dependency JSON: an empty official manualdependence template
does not establish how a current editor serializes non-empty manual entries.
Use repeated --model/--effect/--sound/--icon arguments with IDs used by Lua.
"""
import argparse
import json
from pathlib import Path


KINDS = ('model', 'effect', 'sound', 'icon')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def saved_ids(document, field):
    value = document.get(field, [])
    if isinstance(value, dict) and value.get('__tuple__') is True:
        value = value.get('items')
    if not isinstance(value, list) or any(type(item) is not int for item in value):
        raise ValueError(f'{field}: unknown dependency serialization; inspect current editor output')
    return set(value)


def audit(map_path, requirements):
    map_path = Path(map_path).resolve()
    if not (map_path / 'header.map').is_file():
        raise ValueError(f'Not a Y3 map directory: {map_path}')
    cloud = read_json(map_path / 'cloudresdependence.json')
    manual = read_json(map_path / 'manualdependence.json')
    # A native unit model is a documented dependency source, but only editor
    # save can prove that the current derived download manifest contains it.
    native_models = set()
    for path in (map_path / 'editor_table/editorunit').glob('*.json'):
        model = read_json(path).get('model')
        if type(model) is int:
            native_models.add(model)
    result = {}
    for kind in KINDS:
        required = set(requirements.get(kind, []))
        if any(type(value) is not int or value <= 0 for value in required):
            raise ValueError(f'{kind}: expected positive integer resource IDs')
        field = 'editor_' + kind
        declared = saved_ids(cloud, field) | saved_ids(manual, field)
        missing = required - declared
        pending = missing & native_models if kind == 'model' else set()
        result[kind] = {
            'requested': sorted(required),
            'in_saved_dependency_files': sorted(required & declared),
            'native_unit_reference_pending_editor_save': sorted(pending),
            'not_in_saved_dependency_files': sorted(missing - pending),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', required=True, type=Path, help='Map folder containing header.map')
    for kind in KINDS:
        parser.add_argument('--' + kind, type=int, action='append', default=[], help='Resource ID; repeat for multiple IDs')
    args = parser.parse_args()
    report = audit(args.map, {kind: getattr(args, kind) for kind in KINDS})
    print(json.dumps({'map': str(args.map.resolve()), 'resources': report,
                      'limitations': 'Read-only saved-state audit. Native references may await editor save; custom OriginalRes packages may be restored by refresh. No download or rendering success is inferred.'}, ensure_ascii=False, indent=2))
    missing = any(row['not_in_saved_dependency_files'] or row['native_unit_reference_pending_editor_save'] for row in report.values())
    raise SystemExit(1 if missing else 0)


if __name__ == '__main__':
    main()

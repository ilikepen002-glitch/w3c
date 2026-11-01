"""Inspect Y3 launch state before requesting another editor/game process.

This is a read-only preflight. Pending Windows consent is treated as a launch
in progress. An MCP request being accepted never proves editor/game readiness.
"""
import json
import socket
import subprocess


def port_open(port):
    with socket.socket() as connection:
        connection.settimeout(0.5)
        return connection.connect_ex(('127.0.0.1', port)) == 0


def inspect():
    command = (
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -in 'Game_x64h.exe','Editor.exe','consent.exe' } | "
        "Select-Object Name,ProcessId,ParentProcessId | ConvertTo-Json -Compress"
    )
    output = subprocess.check_output(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
        text=True, encoding='utf-8', timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW,
    ).strip()
    processes = json.loads(output) if output else []
    if isinstance(processes, dict):
        processes = [processes]
    ports = {str(p): port_open(p) for p in (8765, 8766, 8767, 19191)}
    consent_pending = any(p['Name'] == 'consent.exe' for p in processes)
    engine_present = any(p['Name'] in ('Game_x64h.exe', 'Editor.exe') for p in processes)
    state = 'awaiting_windows_consent' if consent_pending else (
        'engine_present_inspect_identity' if engine_present else 'stopped'
    )
    return {
        'state': state, 'processes': processes, 'ports': ports,
        'may_request_editor_launch': not consent_pending and not engine_present and not ports['8765'],
        'note': 'Read map identity and helper client slots before reusing. Never duplicate a pending launch. '
                'Windows consent must be handled by the user; this tool does not approve it.',
    }


if __name__ == '__main__':
    print(json.dumps(inspect(), ensure_ascii=False, indent=2))

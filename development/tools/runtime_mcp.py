"""Call the official runtime MCP's UI events (not desktop/mouse automation)."""
import json
import sys
import urllib.request

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def request(serial, method, params):
    body = json.dumps(dict(jsonrpc='2.0', id=serial, method=method, params=params)).encode()
    req = urllib.request.Request('http://127.0.0.1:8767/mcp', body,
        {'Content-Type':'application/json','Accept':'application/json, text/event-stream'})
    with opener.open(req, timeout=30) as response:
        raw = response.read().decode()
    records = [json.loads(line[5:].strip()) for line in raw.splitlines() if line.startswith('data:')]
    result = records[-1] if records else json.loads(raw)
    if 'error' in result or result.get('result',{}).get('isError'):
        raise RuntimeError(result)
    return result

request(1,'initialize',dict(protocolVersion='2024-11-05',capabilities={},clientInfo=dict(name='Y3MapValidation',version='1')))
for i, path in enumerate(sys.argv[1:], 2):
    print(json.dumps(request(i,'tools/call',dict(name='trigger_ui_touch_event_by_path',arguments=dict(ui_path=path,touch='左键'))),ensure_ascii=False),flush=True)

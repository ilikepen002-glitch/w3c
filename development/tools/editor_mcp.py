"""Client for the running editor's advertised local MCP/SSE endpoint."""
import json, queue, threading, urllib.request, sys, time
from pathlib import Path

BASE = 'http://127.0.0.1:8765'
messages = queue.Queue()
endpoint = queue.Queue()

def listen():
    with urllib.request.urlopen(BASE + '/mcp', timeout=60) as response:
        event = ''
        for raw in response:
            line = raw.decode('utf-8').strip()
            if line.startswith('event:'):
                event = line[6:].strip()
            elif line.startswith('data:'):
                value = json.loads(line[5:].strip())
                (endpoint if 'uri' in value else messages).put(value)

threading.Thread(target=listen, daemon=True).start()
url = BASE + endpoint.get(timeout=10)['uri']
serial = 0

def request(method, params=None, notification=False):
    global serial
    serial += 1
    payload = {'jsonrpc': '2.0', 'method': method, 'params': params or {}}
    if not notification:
        payload['id'] = serial
    req = urllib.request.Request(url, json.dumps(payload).encode(), {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=90) as response:
        body = response.read()
    if notification:
        return
    if body:
        direct = json.loads(body)
        if direct.get('id') == serial:
            return direct
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        result = messages.get(timeout=max(1, deadline-time.monotonic()))
        if result.get('id') == serial:
            return result
    raise TimeoutError(method)

request('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'Y3MapDevelopment', 'version': '1.0'}})
request('notifications/initialized', notification=True)
if len(sys.argv)>1 and sys.argv[1]=='--batch':
    jobs=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8-sig'))
    result=[]
    for job in jobs:
        reply=request('tools/call',job)
        result.append({'name':job['name'],'arguments':job.get('arguments',{}),'reply':reply})
        summary=json.dumps(result[-1], ensure_ascii=False)
        print(summary if len(summary)<2500 else job['name']+': full result saved ('+str(len(summary))+' characters)', flush=True)
        Path(sys.argv[2]+'.results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    sys.exit(0)
elif len(sys.argv) == 1:
    result = request('tools/list')
    Path(__file__).with_name('editor-tools.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    result = [t['name'] for t in result['result']['tools']]
else:
    result = request('tools/call', {'name': sys.argv[1], 'arguments': json.loads(sys.argv[2]) if len(sys.argv)>2 else {}})
print(json.dumps(result, ensure_ascii=False, indent=2))

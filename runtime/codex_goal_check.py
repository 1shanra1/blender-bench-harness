"""Submit one native Codex goal and observe its events; never reprompt."""
import json
import os
import subprocess
from pathlib import Path

from event_log import EventLog

OBJECTIVE = """Verify this Blender installation. Use Blender MCP to inspect the default scene, create a viewport preview at /workspace/viewport.png, open that PNG with your image-viewing tool, and briefly describe what you see. Preserve the scene geometry. Direct screenshot tools return black images on this virtual display; bpy.ops.render.opengl(write_still=True, view_context=True) with a VIEW_3D area and WINDOW region override works. Do not download anything. Finish once you have visually inspected the preview."""
OBJECTIVE = os.environ.get('BENCH_OBJECTIVE', OBJECTIVE)


def main():
    home = Path('/root/.codex')
    home.mkdir(exist_ok=True)
    gemini_provider = 'AI_GATEWAY_API_KEY' in os.environ or 'OPENROUTER_API_KEY' in os.environ
    if 'AI_GATEWAY_API_KEY' in os.environ:
        config = '/opt/bench/codex-vercel.toml'
    elif 'OPENROUTER_API_KEY' in os.environ:
        config = '/opt/bench/codex-openrouter.toml'
    else:
        auth = home / 'auth.json'
        auth.write_text(os.environ.pop('CODEX_AUTH_JSON'))
        auth.chmod(0o600)
        config = '/opt/bench/codex.toml'
    (home / 'config.toml').write_bytes(Path(config).read_bytes())
    Path('/workspace').mkdir(exist_ok=True)
    with open('/tmp/codex-server.log', 'w') as stderr, EventLog('/tmp/codex-events.jsonl') as events:
        server = subprocess.Popen(['codex', 'app-server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr, text=True)
        sequence = 0
        complete = False
        last_goal_status = None

        def send(method, params, request_id=None):
            message = {'method': method, 'params': params}
            if request_id is not None:
                message['id'] = request_id
            server.stdin.write(json.dumps(message) + '\n')
            server.stdin.flush()

        def receive():
            nonlocal complete, last_goal_status
            line = server.stdout.readline()
            if not line:
                raise RuntimeError('Codex app server disconnected')
            events.write(line)
            events.flush()
            message = json.loads(line)
            method = message.get('method')
            params = message.get('params', {})
            if method == 'thread/goal/updated':
                status = params['goal']['status']
                if status != last_goal_status:
                    print('Native goal status:', status, flush=True)
                    last_goal_status = status
                complete = status == 'complete'
                # Read through turn/completed to preserve provider error details.
            if method == 'item/completed':
                item = params.get('item', {})
                print('Completed:', item.get('type'), item.get('tool', ''), flush=True)
                if item.get('type') == 'agentMessage':
                    print(item.get('text', ''), flush=True)
            if 'id' in message and 'method' in message:
                raise RuntimeError(f'Unexpected interactive request: {method}')
            return message

        def request(method, params):
            nonlocal sequence
            sequence += 1
            send(method, params, sequence)
            while True:
                message = receive()
                if message.get('id') == sequence:
                    if 'error' in message:
                        raise RuntimeError(str(message['error']))
                    return message['result']

        try:
            request('initialize', {'clientInfo': {'name': 'blender_bench_smoke', 'version': '0.1.0'}, 'capabilities': {'experimentalApi': True}})
            send('initialized', {})
            models = request('model/list', {})
            print('Gemini catalog entries:', [m['model'] for m in models['data'] if 'gemini-3.8' in m['model']], flush=True)
            thread = request('thread/start', {'cwd': '/workspace', 'approvalPolicy': 'never', 'sandbox': 'danger-full-access'})
            print('Selected model:', thread.get('model'), 'effort:', thread.get('reasoningEffort'), flush=True)
            if gemini_provider and (thread.get('model') != 'google/gemini-3.8-flash' or thread.get('reasoningEffort') != 'high'):
                raise RuntimeError('Requested Gemini model and High effort were not selected')
            request('thread/goal/set', {'threadId': thread['thread']['id'], 'objective': OBJECTIVE, 'status': 'active'})
            while True:
                event = receive()
                if event.get('method') == 'turn/completed':
                    if event['params']['turn']['status'] != 'completed':
                        raise RuntimeError(str(event['params']['turn']))
                    if complete:
                        break
                    if last_goal_status != 'active':
                        raise RuntimeError(f'Native goal stopped: {last_goal_status}')
            Path('/tmp/bench-native-result.json').write_text(json.dumps({'complete': True}))
            print('Native goal completed.', flush=True)
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == '__main__':
    main()

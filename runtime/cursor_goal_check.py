"""Submit one native Cursor goal with Gemini and scoped tool permissions."""
import json
import os
import subprocess
from pathlib import Path

MODEL = 'gemini-3.6-flash-minimal'
OBJECTIVE = """Verify this Blender installation. Use Blender MCP to inspect the default scene, create a viewport preview at /workspace/viewport.png, open the PNG with your image-reading tool, and briefly describe what you see. Preserve scene geometry. Direct screenshots return black images on this virtual display; bpy.ops.render.opengl(write_still=True, view_context=True) with a VIEW_3D area and WINDOW region override works. Use MCP and image reading only, no shell commands or downloads. Finish once you have visually inspected the preview."""
MODEL = os.environ.get('BENCH_MODEL', MODEL)
OBJECTIVE = os.environ.get('BENCH_OBJECTIVE', OBJECTIVE)
EXPERIMENT = os.environ.get('BENCH_EXPERIMENT') == '1'


def main():
    auth = Path('/root/.config/cursor/auth.json')
    auth.parent.mkdir(parents=True, exist_ok=True)
    auth.write_text(os.environ.pop('CURSOR_AUTH_JSON'))
    auth.chmod(0o600)
    # Runtime asset/plugin downloads are disallowed; fail SSH fetches immediately.
    os.environ['GIT_SSH_COMMAND'] = '/bin/false'
    config = Path('/workspace/.cursor')
    config.mkdir(parents=True, exist_ok=True)
    (config / 'mcp.json').write_text(json.dumps({'mcpServers': {'blender': {
        'command': 'runuser', 'args': ['-u', 'blender', '--', 'blender-mcp']
    }}}))
    permissions = {
        'allow': [
            'Read(/workspace/**)',
            'Write(/workspace/**)',
            'Shell(*)',
            'Mcp(blender:get_objects_summary)',
            'Mcp(blender:get_blendfile_summary_datablocks)',
            'Mcp(blender:search_api_docs)',
            'Mcp(blender:execute_blender_code)',
        ],
        'deny': [
            'WebFetch(*)',
            'Read(/root/**)',
            'Write(/root/**)',
        ],
    }
    (config / 'cli.json').write_text(json.dumps({'permissions': permissions}, indent=2))
    command = ['cursor-agent', '--model', MODEL, '--print', '--output-format', 'stream-json',
               '--sandbox', 'disabled', '--approve-mcps', '--trust',
               '--workspace', '/workspace', '/goal ' + OBJECTIVE]
    goal_created = goal_complete = image_read = False
    with open('/tmp/cursor-stderr.log', 'w') as stderr, open('/tmp/cursor-events.jsonl', 'w') as events:
        # Cursor loads project permissions from cwd, independently of --workspace.
        process = subprocess.Popen(command, cwd='/workspace', stdout=subprocess.PIPE, stderr=stderr, text=True)
        try:
            for line in process.stdout:
                events.write(line)
                events.flush()
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    print(line, end='', flush=True)
                    continue
                kind = event.get('type')
                if kind == 'tool_call':
                    if event.get('subtype') == 'completed':
                        calls = event.get('tool_call', {})
                        goal_created |= 'success' in calls.get('createGoalToolCall', {}).get('result', {})
                        goal_complete |= calls.get('updateGoalToolCall', {}).get('result', {}).get('success', {}).get('status') == 'GOAL_STATUS_COMPLETE'
                        read = calls.get('readToolCall', {})
                        image_read |= read.get('args', {}).get('path') == '/workspace/viewport.png' and 'success' in read.get('result', {})
                    print('Tool:', event.get('subtype'), list(event.get('tool_call', {}).keys()), flush=True)
                elif kind == 'system':
                    print('System:', {k: v for k, v in event.items() if k in ('type', 'subtype', 'model')}, flush=True)
                elif kind in ('assistant', 'result'):
                    print(json.dumps(event)[:2000], flush=True)
            process.wait()
            if process.returncode:
                raise RuntimeError(f'Cursor exited with {process.returncode}')
            Path('/tmp/bench-native-result.json').write_text(json.dumps({'complete': goal_created and goal_complete}))
            if not (goal_created and goal_complete and (EXPERIMENT or image_read)):
                raise RuntimeError('Native goal completion and viewport reading were not both verified; inspect event log')
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


if __name__ == '__main__':
    main()

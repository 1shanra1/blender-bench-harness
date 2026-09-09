"""Submit a single native Antigravity goal and capture emitted events."""
import json
import os
import subprocess
from pathlib import Path

from event_log import EventLog

MODEL = 'gemini-3.6-flash-low'
OBJECTIVE = """Verify this Blender installation. Use Blender MCP to inspect the default scene, create a viewport preview at /workspace/viewport.png, open the PNG with your image-reading tool, and briefly describe what you see. Preserve scene geometry. Direct screenshots return black images on this virtual display; bpy.ops.render.opengl(write_still=True, view_context=True) with a VIEW_3D area and WINDOW region override works. Use MCP and image reading only, no shell commands or downloads. Finish once you have visually inspected the preview."""
MODEL = os.environ.get('BENCH_MODEL', MODEL)
OBJECTIVE = os.environ.get('BENCH_OBJECTIVE', OBJECTIVE)
EXPERIMENT = os.environ.get('BENCH_EXPERIMENT') == '1'


def main():
    config = Path('/root/.gemini/antigravity-cli')
    config.mkdir(parents=True, exist_ok=True)
    auth = config / 'antigravity-oauth-token'
    auth.write_text(os.environ.pop('AGY_AUTH_TOKEN'))
    auth.chmod(0o600)
    permissions = {
        'allow': [
            'read_file(/root/.gemini/antigravity-cli/builtin)',
            'read_file(/workspace)',
            'write_file(/workspace)',
            'command(*)',
            'mcp(blender/get_objects_summary)',
            'mcp(blender/get_blendfile_summary_datablocks)',
            'mcp(blender/search_api_docs)',
            'mcp(blender/execute_blender_code)',
        ],
        'deny': [
            'read_url(*)',
            'execute_url(*)',
            'read_file(/root/.gemini/antigravity-cli/antigravity-oauth-token)',
        ],
    }
    (config / 'settings.json').write_text(json.dumps({'permissions': permissions}, indent=2))
    mcp = Path('/root/.gemini/config')
    mcp.mkdir(parents=True, exist_ok=True)
    (mcp / 'mcp_config.json').write_text(json.dumps({'mcpServers': {'blender': {
        'command': 'sh',
        'args': ['/opt/bench/start_mcp.sh', 'runuser', '-u', 'blender', '--', 'blender-mcp'],
        'timeoutSeconds': 600,
    }}}))
    command = ['agy', '--model', MODEL, '--print-timeout', os.environ.get('BENCH_SECONDS', '180') + 's',
               '--output-format', 'stream-json', '-p', '/goal ' + OBJECTIVE]
    native_goal = image_read = complete = False
    with open('/tmp/agy-stderr.log', 'w') as stderr, EventLog('/tmp/agy-events.jsonl') as events:
        process = subprocess.Popen(command, cwd='/workspace', stdout=subprocess.PIPE, stderr=stderr, text=True)
        try:
            for line in process.stdout:
                events.write(line)
                events.flush()
                event = json.loads(line)
                native_goal |= any(c.get('name') == 'goal' and c.get('type') == 'system'
                                   for c in event.get('init', {}).get('expanded_commands', []))
                step = event.get('step_update', {})
                image_read |= (step.get('state') == 'DONE' and step.get('tool_name') == 'view_file'
                               and step.get('tool_info', {}).get('parameters', {}).get('AbsolutePath') == '/workspace/viewport.png')
                result = event.get('result', {})
                complete |= result.get('status') == 'SUCCESS' and '<!-- GOAL_COMPLETE -->' in result.get('response', '')
                print(line[:1800], end='', flush=True)
            process.wait()
            if process.returncode:
                raise RuntimeError(f'Antigravity exited with {process.returncode}')
            Path('/tmp/bench-native-result.json').write_text(json.dumps({'complete': native_goal and complete}))
            if not (native_goal and complete and (EXPERIMENT or image_read)):
                raise RuntimeError('Native goal completion and viewport reading were not both verified')
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


if __name__ == '__main__':
    main()

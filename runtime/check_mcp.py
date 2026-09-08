"""Use the official MCP server to save a viewport preview in the sandbox."""
import asyncio
import socket
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

VIEWPORT_CODE = """
import bpy
scene = bpy.context.scene
scene.render.resolution_x = 1280
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = '/tmp/viewport.png'
window = bpy.context.window_manager.windows[0]
area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
with bpy.context.temp_override(window=window, area=area, region=region):
    bpy.ops.render.opengl(write_still=True, view_context=True)
result = {'filepath': scene.render.filepath, 'blender_version': bpy.app.version_string}
"""


async def main():
    for _ in range(60):
        try:
            with socket.create_connection(("127.0.0.1", 9876), timeout=1):
                break
        except OSError:
            await asyncio.sleep(1)
    else:
        raise RuntimeError("Blender MCP bridge did not start")
    async with stdio_client(StdioServerParameters(command="blender-mcp")) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("execute_blender_code", {"code": VIEWPORT_CODE})
            if result.isError:
                raise RuntimeError(str(result.content))
            for part in result.content:
                if part.type == 'text':
                    print(part.text)
            image = Path('/tmp/viewport.png').read_bytes()
            if not image.startswith(b'\x89PNG\r\n\x1a\n'):
                raise RuntimeError('Viewport preview is not a PNG')
            print(f'MCP created viewport preview ({len(image)} bytes)')


if __name__ == "__main__":
    asyncio.run(main())

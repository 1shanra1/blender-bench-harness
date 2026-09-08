"""Enable the official MCP add-on in a fresh interactive Blender session."""
import addon_utils
import bpy

addon_utils.enable("blender_mcp_addon", default_set=True, persistent=True)
bpy.context.preferences.view.show_splash = False
bpy.ops.blmcp.server_start()

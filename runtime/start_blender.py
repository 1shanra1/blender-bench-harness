"""Enable the official MCP add-on in a fresh interactive Blender session."""
import addon_utils
import bpy

# Keep localhost MCP access, but do not fetch the online asset catalog.
bpy.context.preferences.asset_libraries.use_online_essentials = False
addon_utils.enable("blender_mcp_addon", default_set=True, persistent=True)
bpy.context.preferences.view.show_splash = False
bpy.ops.blmcp.server_start()

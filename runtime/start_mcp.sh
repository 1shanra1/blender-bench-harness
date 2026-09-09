#!/bin/sh
# Keep protocol messages on stdout; collect server diagnostics separately.
exec "$@" 2>>/tmp/blender-mcp.log

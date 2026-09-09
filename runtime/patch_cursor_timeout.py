"""Patch the MCP wait limit in Cursor CLI 2026.09.02-c22c1a3."""
import hashlib
from pathlib import Path

bundle = Path('/opt/cursor/index.js')
original = bundle.read_bytes()
expected_sha256 = '32e4603ed58aebfb548b1742411da116baf55179160576e92fb7ded23aafc193'
if hashlib.sha256(original).hexdigest() != expected_sha256:
    raise RuntimeError('Cursor bundle changed; review the timeout patch before building.')

old_call = b'this.client.callTool({name:t,arguments:n})'
new_call = b'this.client.callTool({name:t,arguments:n},undefined,{timeout:600000})'
if original.count(old_call) != 1:
    raise RuntimeError('Expected exactly one Cursor MCP call to patch.')

bundle.write_bytes(original.replace(old_call, new_call))
print('Patched Cursor MCP tool timeout to 600 seconds.')

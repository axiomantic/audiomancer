# Boot - TidalCycles Session Startup

Boot the TidalCycles live coding environment using the audiomancer MCP server.

## Execution

Call the `boot_session` MCP tool from audiomancer:

```
mcp__audiomancer__boot_session
```

This will:

1. Open VS Code to `session.tidal`
1. Open SuperCollider with `start_superdirt.scd`
1. Return session info with enabled samples and quick reference

## Optional: Auto-execute SuperDirt

To attempt automatic execution of the SuperDirt startup script (requires Accessibility permissions):

```
mcp__audiomancer__boot_session { "execute_superdirt": true }
```

If permissions are not granted, the tool will still open the files and provide instructions.

## After Boot

1. In SuperCollider, press **Cmd+Shift+Enter** to execute `start_superdirt.scd`
1. Wait for "SuperDirt started on port 57120" message
1. In VS Code, evaluate TidalCycles code with **Shift+Enter** (line) or **Ctrl+Enter** (block)

## Quick Reference

```haskell
d1 $ sound "bd bd bd bd"  -- Play pattern on channel 1
d2 $ sound "hh*8"         -- Play hi-hats on channel 2
hush                       -- Stop all channels
d1 $ silence              -- Stop channel 1
```

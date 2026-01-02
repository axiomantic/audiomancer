# audiomancer MCP server demo
Output docs/assets/gifs/mcp-demo.gif

Set Shell "bash"
Set Theme "Dracula"
Set FontSize 14
Set Width 900
Set Height 400
Set Padding 20

Hide
Type "unset VIRTUAL_ENV && cd ~/Development/audiomancer"
Enter
Sleep 500ms
Show

Type "uv run audiomancer serve"
Enter
Sleep 2s

Ctrl+C
Sleep 500ms

Type "echo 'MCP tools: search_samples, generate_pattern, analyze_file, list_packs'"
Enter
Sleep 2s

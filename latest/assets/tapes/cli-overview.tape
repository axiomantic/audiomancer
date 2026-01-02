# audiomancer CLI overview demo
Output docs/assets/gifs/cli-overview.gif

Set Shell "bash"
Set Theme "Dracula"
Set FontSize 14
Set Width 900
Set Height 500
Set Padding 20

# Clear any inherited venv
Hide
Type "unset VIRTUAL_ENV && cd ~/Development/audiomancer"
Enter
Sleep 500ms
Show

Type "uv run audiomancer --help"
Enter
Sleep 3s

Type "uv run audiomancer doctor"
Enter
Sleep 4s

Type "uv run audiomancer stats"
Enter
Sleep 3s

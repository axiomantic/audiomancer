# audiomancer search demo
Output docs/assets/gifs/search.gif

Set Shell "zsh"
Set Theme "Dracula"
Set FontSize 14
Set Width 900
Set Height 500
Set Padding 20

Type "cd ~/Development/audiomancer"
Enter
Sleep 500ms

Type "# Search for samples"
Enter
Sleep 500ms

Type "uv run audiomancer search kick"
Enter
Sleep 3s

Type "# Search with filters"
Enter
Sleep 500ms

Type 'uv run audiomancer search --bpm 120-130 --key Am'
Enter
Sleep 3s

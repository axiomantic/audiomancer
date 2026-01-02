# audiomancer search demo
Output docs/assets/gifs/search.gif

Set Shell "bash"
Set Theme "Dracula"
Set FontSize 14
Set Width 900
Set Height 500
Set Padding 20

Hide
Type "unset VIRTUAL_ENV && cd ~/Development/audiomancer"
Enter
Sleep 500ms
Show

Type "uv run audiomancer search kick"
Enter
Sleep 3s

Type "uv run audiomancer search --bpm 120-130 --key Am"
Enter
Sleep 3s

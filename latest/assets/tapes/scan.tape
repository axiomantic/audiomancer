# audiomancer scan demo
Output docs/assets/gifs/scan.gif

Set Shell "zsh"
Set Theme "Dracula"
Set FontSize 14
Set Width 900
Set Height 450
Set Padding 20

Type "cd ~/Development/audiomancer"
Enter
Sleep 500ms

Type "# Scan a sample library with parallel workers"
Enter
Sleep 1s

Type "uv run audiomancer scan ~/Music/Samples --workers 4"
Enter
Sleep 6s

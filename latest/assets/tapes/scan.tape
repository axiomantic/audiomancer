# audiomancer scan demo
Output docs/assets/gifs/scan.gif

Set Shell "bash"
Set Theme "Dracula"
Set FontSize 14
Set Width 900
Set Height 450
Set Padding 20

Hide
Type "unset VIRTUAL_ENV && cd ~/Development/audiomancer"
Enter
Sleep 500ms
Show

Type "uv run audiomancer scan ~/Music/Samples --workers 4"
Enter
Sleep 6s

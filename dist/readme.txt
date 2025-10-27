LegoPy v1.0 Instructions
------------------------
1. Copy `LegoPy.exe` and this file to any folder where you want to run the app (a local drive, Desktop, or a shared network path).
2. Double-click `LegoPy.exe` to start. On first launch, Windows SmartScreen may warn about an unrecognized app; choose “More info” and then “Run anyway.”
3. No installation is needed. The executable unpacks itself to a temporary folder while it runs and closes cleanly when you exit the app.
4. The application writes temporary diagnostic logs (for ffmpeg activity) next to the executable. You can delete them after use if you do not need the logs.

Troubleshooting:
- If video export features fail, ensure the target drive has write permissions and enough free space for the generated clips.
- If you see errors about missing ffmpeg, re-run the app from the original `LegoPy.exe`; the embedded ffmpeg binaries are included in the same file.
- Always close the app before moving or deleting project files that the interface is working with, to avoid file access errors.

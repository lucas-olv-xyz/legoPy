# LegoPy Project Overview

## What This App Does

- LegoPy is a desktop helper that stitches short "Tip" videos together with optional "Hook" clips for the same project code.
- It keeps every compilation at or above two minutes, so each exported video matches our delivery rules.
- Two workspaces cover the different stages of production: the first batch you send to clients and the follow-up batches you build later.

## Typical Workflow

1. Open the app and type the three digits of the project code (for example, 123 becomes E123).
2. Choose **First Batch** for the very first delivery or **Next Batch** for follow-up rounds.
3. Use the buttons to load Tip clips and, when needed, Hook clips from your computer.
4. Review the lists, drag files up or down with the arrow buttons, and rename compilations when it helps communication.
5. Press the export buttons. The app glues the clips together with FFmpeg (bundled with the project) and saves the finished videos into the correct folders.

## Screens You Will See

- **First Batch screen** - Automatically creates several Tip compilations by rotating the order of the files you load. You can still add empty compilations and build one manually if you prefer. A single click can export every Tip list and the matching Hook + Tip sequences.
- **Next Batch screen** - Lets you curate each compilation by hand. You decide column layout, duplicate any compilation you like, and combine Hooks with Tips automatically. Only the compilations you mark for export are produced.

## What Gets Exported

- Tip compilations (with or without Hooks) are saved inside a `2min` folder next to the original clips.
- First-batch sequences (Hook + Tips) land in `sequences/comp1`.
- Follow-up sequences created in the Next Batch screen land in `sequences/comp2`.
- File names always start with the project code and sequence markers (for example, `E123V0H1.mp4`) so everything stays organized when we send files out.

## What's Inside This Repository

- `main.py` - Launches the Tkinter window and swaps between the First Batch and Next Batch screens.
- `first_batch_frame.py` - Screen logic for the first delivery.
- `next_batch_frame.py` - Screen logic for subsequent deliveries.
- `compilations.py` - Reusable widgets for file lists and the rules for exporting the videos.
- `utils.py` - Helper functions that locate the FFmpeg tools, check video details, and handle folder creation.
- `ffmpeg-bin/` - Portable FFmpeg and FFprobe executables used during export.
- `exe/` - Everything related to the packaged executable (`build/`, `dist/`, and `main.spec`).
- `venv/` - Optional Python virtual environment that keeps project dependencies separate.
- `.idea/` - JetBrains IDE settings for teammates who use PyCharm.

## Troubleshooting and Logs

- If an export fails, the app writes a short log (`duration_diag.log`, `ffmpeg_concat_diag.log`, `ffmpeg_trim_diag.log`, `tips_export_error.log`, or `sequence_export_error.log`) next to the source clips. Check these files for clues.
- A common reason for export failure is mixing clips that were rendered in different resolutions. The app stops early and shows a message if that happens.

## Requirements and How to Run

- Python 3 with Tkinter (already included in standard Python installs).
- FFmpeg and FFprobe are already bundled inside `ffmpeg-bin/`, so no extra install is needed.
- For development, activate the virtual environment if you use it and run `python main.py`.
- For a packaged app, use the files under `exe/` or rebuild them with `pyinstaller exe/main.spec`.

## Tips

- Use the Export checkbox on each compilation to keep drafts in the list while exporting only the final selections.
- When sharing the packaged app, always include the `ffmpeg-bin` folder so the export buttons keep working.

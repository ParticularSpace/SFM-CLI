# SFM CLI (Super File Manager)

A simple, numbered-menu Python file manager. No database or activity log.

## Setup

```powershell
python -m pip install -r requirements.txt
python main.py
```

The `send2trash` dependency is needed only for moving duplicate files to the Recycle Bin. Other features use Python's standard library.

## Features

1. **Organize Downloads:** Preview and sort top-level files into Documents, Images, Videos, Audio, Archives, Installers, and Other subfolders. You can change the folder from the submenu.
2. **Find Duplicates:** Scan folders recursively, compare file sizes and SHA-256 hashes, then optionally move extra copies to the Recycle Bin. Prefers keeping files without `(1)`, `(2)`, etc. in the name.
3. **Find Large Files:** List files above a chosen size threshold without changing them.

Each action prints a result message. The program does not save an activity log or JSON history.

## Safety

- Organizing requires a preview and typing `YES` to confirm.
- Duplicate cleanup previews the files to keep and trash, then requires typing `DELETE`.
- The Recycle Bin can restore trashed duplicate copies (subject to your system settings), **but it cannot undo file moves made by Organize Downloads**.
- A file can be an intentional duplicate even if its contents match. Check the preview.
- File moves do not overwrite existing names intentionally; a numbered name is used instead.
- Avoid running multiple copies at once and test with sample files first. File operations are not transactional.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Files

- `main.py` — menu, organizing, duplicate scanning/cleanup, large-file scanning
- `tests/` — automated tests
- `requirements.txt` — Recycle Bin support

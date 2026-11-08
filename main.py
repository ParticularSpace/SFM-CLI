"""SFM CLI (Super File Manager) - a simple menu-based file organizer."""

import hashlib
import os
import re
import shutil
from pathlib import Path

DOWNLOADS = Path.home() / "Downloads"

FILE_TYPES = {
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".csv", ".xls", ".xlsx", ".ppt", ".pptx"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".svg"},
    "Videos": {".mp4", ".mov", ".avi", ".mkv", ".webm"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".ogg"},
    "Archives": {".zip", ".tar", ".gz", ".7z", ".rar"},
    "Installers": {".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm"},
}


def heading(title):
    print(f"\n=== {title.upper()} ===")


def confirmation(message):
    """Show a clear result after an action finishes."""
    print(f"\n[RESULT] {message}")


def pause():
    input("\nPress Enter to continue...")


def menu(title, options):
    """Print numbered options and keep asking until the choice is valid."""
    while True:
        heading(title)
        for number, label in options.items():
            print(f"{number}. {label}")
        choice = input("\nSelect an option: ").strip()
        if choice in options:
            return choice
        print("Invalid selection. Choose a number from the menu.")


def choose_folder(current):
    """Only ask for a path when the user chooses to change folders."""
    print(f"\nCurrent folder: {current}")
    print("Enter a folder path, or press Enter to cancel.")
    answer = input("Folder path: ").strip().strip('"')
    if not answer:
        return current
    folder = Path(answer).expanduser()
    if not folder.is_dir():
        confirmation("Folder not found. No changes made.")
        return current
    confirmation(f"Folder changed to: {folder.resolve()}")
    return folder.resolve()


def file_category(file):
    for name, extensions in FILE_TYPES.items():
        if file.suffix.lower() in extensions:
            return name
    return "Other"


def available_name(destination, reserved):
    """Avoid overwriting a file if the destination name already exists."""
    candidate = destination
    number = 1
    while candidate.exists() or str(candidate) in reserved:
        candidate = destination.with_name(f"{destination.stem} ({number}){destination.suffix}")
        number += 1
    reserved.add(str(candidate))
    return candidate


def organize_files(folder):
    # Only organize files directly inside this folder, not its subfolders.
    files = sorted(file for file in folder.iterdir() if file.is_file() and not file.is_symlink())
    if not files:
        confirmation("Nothing to organize. This folder has no top-level files.")
        return

    reserved = set()
    changes = []
    for file in files:
        destination = available_name(folder / file_category(file) / file.name, reserved)
        changes.append({"original": str(file), "destination": str(destination), "state": "planned"})

    heading("Preview - No Files Changed")
    for change in changes:
        target = Path(change["destination"])
        print(f"{Path(change['original']).name}  ->  {target.parent.name}/{target.name}")
    print(f"\nFiles to move: {len(changes)}")
    if input("\nType YES to move these files (anything else cancels): ").strip() != "YES":
        confirmation("Cancelled. No files moved.")
        return

    moved = 0
    for change in changes:
        original = Path(change["original"])
        destination = Path(change["destination"])
        try:
            # Check the paths again because files may change after the preview.
            if not original.is_file() or original.is_symlink() or destination.exists():
                raise OSError("Source missing or destination already exists")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(original), str(destination))
            moved += 1
        except (OSError, shutil.Error) as error:
            print(f"Could not move {original.name}: {error}")

    confirmation(f"Organization finished: {moved} of {len(changes)} files moved.")


def organize_menu():
    folder = DOWNLOADS
    while True:
        print(f"\nCurrent folder: {folder}")
        choice = menu("Organize Files", {"1": "Preview and Organize", "2": "Change Folder", "0": "Back"})
        if choice == "0":
            return
        if choice == "2":
            folder = choose_folder(folder)
        elif not folder.is_dir():
            confirmation("Folder not found. Choose another folder first.")
            pause()
        else:
            organize_files(folder)
            pause()


def hash_file(path):
    sha = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def scan_files(folder):
    """Walk subfolders but do not follow directory shortcuts/symlinks."""
    for root, directories, names in os.walk(folder, followlinks=False):
        directories[:] = [name for name in directories if not (Path(root) / name).is_symlink()]
        for name in names:
            path = Path(root) / name
            if not path.is_symlink():
                yield path


def duplicate_groups(folder):
    """Group identical files by size first, then by their SHA-256 hash."""
    by_size = {}
    for path in scan_files(folder):
        try:
            if path.is_file():
                by_size.setdefault(path.stat().st_size, []).append(path)
        except OSError:
            continue

    groups = []
    for paths in by_size.values():
        if len(paths) < 2:
            continue
        by_hash = {}
        for path in paths:
            try:
                by_hash.setdefault(hash_file(path), []).append(path)
            except OSError as error:
                print(f"Skipped {path}: {error}")
        groups.extend(paths for paths in by_hash.values() if len(paths) > 1)
    return groups


def duplicate_sort_key(path):
    """Prefer keeping the original name instead of a copy named (1), (2), etc."""
    numbered_copy = re.search(r" \(\d+\)$", path.stem)
    return (numbered_copy is not None, str(path).lower())


def trash_duplicates(groups):
    """Preview extra copies, then send them to the OS recycle bin/trash."""
    try:
        from send2trash import send2trash
    except ImportError:
        confirmation("Install the recycle-bin support first: python -m pip install send2trash")
        return

    # Keep one file from each group. Prefer a filename without (1), (2), etc.
    extras = []
    for group in groups:
        ordered = sorted(group, key=duplicate_sort_key)
        print(f"\nKEEP: {ordered[0]}")
        for path in ordered[1:]:
            print(f"TRASH: {path}")
            extras.append((ordered[0], path))

    print(f"\nExtra copies: {len(extras)}")
    print("Files will go to your system Recycle Bin / Trash, not be permanently deleted.")
    if input("Type DELETE to send these extras to Trash: ").strip() != "DELETE":
        confirmation("Cancelled. No files removed.")
        return

    removed = 0
    for keeper, extra in extras:
        try:
            # Check again in case a file changed while the menu was open.
            if (not keeper.is_file() or keeper.is_symlink() or
                    not extra.is_file() or extra.is_symlink() or
                    keeper.stat().st_size != extra.stat().st_size or
                    hash_file(keeper) != hash_file(extra)):
                print(f"Skipped (files changed): {extra}")
                continue
            send2trash(str(extra))
            removed += 1
        except OSError as error:
            print(f"Could not trash {extra}: {error}")
    confirmation(f"Duplicate cleanup finished: {removed} of {len(extras)} extra copies sent to Trash.")


def find_duplicates(folder):
    heading("Duplicate Files")
    groups = duplicate_groups(folder)
    if not groups:
        confirmation("Duplicate scan complete: 0 duplicate group(s) found. No files changed.")
        return

    for number, group in enumerate(groups, 1):
        print(f"\nGroup {number}:")
        for path in sorted(group, key=duplicate_sort_key):
            print(f"  {path}")
    confirmation(f"Duplicate scan complete: {len(groups)} duplicate group(s) found. No files changed.")
    choice = menu("Duplicate Actions", {"1": "Move extra copies to Recycle Bin / Trash", "0": "Back"})
    if choice == "1":
        trash_duplicates(groups)


def find_large_files(folder):
    answer = input("\nMinimum file size in MB [100]: ").strip() or "100"
    try:
        minimum = float(answer)
        if minimum < 0 or not minimum < float("inf"):
            raise ValueError
    except ValueError:
        confirmation("Invalid size. Enter a nonnegative number.")
        return

    matches = []
    for path in scan_files(folder):
        try:
            size = path.stat().st_size
            if size >= minimum * 1024 * 1024:
                matches.append((size, path))
        except OSError:
            continue
    heading("Large Files")
    for size, path in sorted(matches, key=lambda item: item[0], reverse=True)[:30]:
        print(f"{size / 1024 / 1024:8.1f} MB  {path}")
    confirmation(f"Large-file scan complete: {len(matches)} file(s) found. Showing up to 30. No files changed.")


def scan_menu(title, scan_function):
    folder = DOWNLOADS
    while True:
        print(f"\nCurrent folder: {folder}")
        choice = menu(title, {"1": "Start Scan", "2": "Change Folder", "0": "Back"})
        if choice == "0":
            return
        if choice == "2":
            folder = choose_folder(folder)
        elif not folder.is_dir():
            confirmation("Folder not found. Choose another folder first.")
            pause()
        else:
            scan_function(folder)
            pause()


def main():
    while True:
        choice = menu("SFM CLI - Super File Manager", {
            "1": "Organize Downloads",
            "2": "Find Duplicates",
            "3": "Find Large Files",
            "0": "Exit",
        })
        if choice == "0":
            print("Goodbye!")
            return
        if choice == "1":
            organize_menu()
        elif choice == "2":
            scan_menu("Find Duplicates", find_duplicates)
        elif choice == "3":
            scan_menu("Find Large Files", find_large_files)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")

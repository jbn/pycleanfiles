# %%
from pathlib import Path
import subprocess
import re

# %%
def find_largest_folders(root_dir: Path) -> list[tuple[Path, int]]:
    """
    Find the largest folders in the given root directory.
    """

    def get_folder_size(folder: Path) -> tuple[Path, int]:
        """
        Get the size of a single folder.
        """
        cmd = f"du -sk {folder}"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            size, _ = result.stdout.split('\t')
            return folder, int(size)
        except subprocess.CalledProcessError:
            # Ignore errors due to permission issues
            return folder, -1

    # Ensure the root_dir is an absolute path
    root_dir = Path(root_dir).resolve()

    # Get sizes for all immediate subdirectories
    folder_sizes = []
    for item in root_dir.iterdir():
        if item.is_dir():
            try:
                folder_sizes.append(get_folder_size(item))
            except RuntimeError:
                # Ignore RuntimeErrors (which might be due to permission issues)
                pass

    # Sort folders by size in descending order
    folder_sizes.sort(key=lambda x: x[1], reverse=True)

    return folder_sizes

def convert_size(size_in_kb: int, units: str = "KB") -> str:
    """
    Convert size in KB to a human-readable format.
    """
    match units:
        case "KB":
            return f"{size_in_kb:,} KB"
        case "MB":
            return f"{size_in_kb / 1024:,.2f} MB"
        case "GB":
            return f"{size_in_kb / 1024 / 1024:,.2f} GB"
        case _:
            raise ValueError(f"Invalid unit: {units}")

def print_largest_human_readable(folders: list[tuple[Path, int]], units: str = "GB") -> None:
    """
    Print the largest folders in a human-readable format.
    """
    for folder, size in folders:
        print(f"{convert_size(size, units):>10}: {folder}")

# %%
my_home_dir = Path.home()
largest_folders = find_largest_folders(my_home_dir)
print_largest_human_readable(largest_folders[:10])

# %%
largest_downloads = find_largest_folders(my_home_dir / "Downloads")
print_largest_human_readable(largest_downloads[:10])


# %%
HOME_DIR = Path.home()

COMMON_REMOVE_PRIORITIES = [
    (HOME_DIR / "Downloads", 10),
]

# %%
def find_duplicates_below(root_dir: Path, min_size_in_kb: int = 10) -> list[tuple[Path, Path, int]]:
    """
    Find duplicate files below the given root directory.
    """
    root_dir = Path(root_dir).resolve()

    # Run fdupes command
    cmd = f"fdupes -r -S -G {min_size_in_kb*100} '{root_dir}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        if 'command not found' in result.stderr:
            raise FileNotFoundError("fdupes command not found. Please install fdupes to use this function.")
        else:
            raise RuntimeError(f"Failed to run fdupes: {result.stderr}")

    # Process the output
    duplicates = []
    current_group: list[Path] = []
    current_size = 0

    for line in result.stdout.split('\n'):
        if line.strip():
            if line[0].isdigit():
                # This is a size line
                if current_group:
                    # Process the previous group
                    for i in range(len(current_group) - 1):
                        duplicates.append((current_group[0], current_group[i+1], current_size))
                    current_group = []
                # Extract the new size
                match = re.search(r'(\d+) bytes', line)
                if match:
                    current_size = int(match.group(1)) // 1024  # Convert bytes to KB
            else:
                # This is a file path
                current_group.append(Path(line.strip()))

    # Process the last group
    if current_group:
        for i in range(len(current_group) - 1):
            duplicates.append((current_group[0], current_group[i+1], current_size))

    # Sort duplicates by size in descending order
    duplicates.sort(key=lambda x: x[2], reverse=True)

    return duplicates


duplicates = find_duplicates_below(my_home_dir / "Downloads", min_size_in_kb=100)
duplicates[:10]
# %%
def print_duplicates(duplicates: list[tuple[Path, Path, int]], units: str = "MB") -> None:
    """
    Print the duplicates in a human-readable format.
    """
    for file1, file2, size in duplicates:
        print(f"{convert_size(size, units):>10}:\n\t{file1}\n\t{file2}")

print_duplicates(duplicates[:10])

# %%
def find_browser_multi_saves(file_paths: list[Path]) -> list[Path]:
    """
    Check if any of the file paths are browser multi-save versions.

    Args:
    file_paths (list[Path]): List of file paths to check.

    Returns:
    list[Path]: List of paths that are identified as browser multi-save versions.
    """
    multi_save_pattern = re.compile(r'^(.+) \(\d+\)(\.[^.]+)$')
    original_names: dict[str, Path] = {}
    multi_saves: list[Path] = []

    for path in file_paths:
        name = path.name
        match = multi_save_pattern.match(name)
        
        if match:
            # This file matches the multi-save pattern
            original_name = f"{match.group(1)}{match.group(2)}"
            if original_name in original_names:
                # We found a multi-save version
                multi_saves.append(path)
            else:
                # Store this as a potential original
                original_names[name] = path
        else:
            # This might be an original file
            original_names[name] = path

    return multi_saves


deleted_amount = 0
for duplicate in duplicates:
    multi_saves = find_browser_multi_saves([duplicate[0], duplicate[1]])
    if multi_saves:
        print(f"{convert_size(duplicate[2], units='MB'):>10}:\n\t{duplicate[0]}\n\t{duplicate[1]}")
        print("\t", multi_saves)
        for s in multi_saves:
            deleted_amount += s.stat().st_size
            s.unlink()
print(f"Deleted {convert_size(deleted_amount, units='MB')}")
            

# %%

#!/usr/bin/env python3
"""
Script to rename files in a folder:
- Lists all files in the specified folder
- If filename contains "DATA", replaces the first underscore with a dash
"""

import os
import sys
from pathlib import Path

def rename_files_with_data(folder_path, dry_run=True):
    """
    Rename files containing 'DATA' by replacing first underscore with dash.
    
    Args:
        folder_path (str): Path to the folder containing files
        dry_run (bool): If True, only shows what would be renamed without actually doing it
    
    Returns:
        int: Number of files that would be/were renamed
    """
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"Error: Folder '{folder_path}' does not exist.")
        return 0
    
    if not folder.is_dir():
        print(f"Error: '{folder_path}' is not a directory.")
        return 0
    
    renamed_count = 0
    
    # Get all files in the folder
    files = [f for f in folder.iterdir() if f.is_file()]
    
    print(f"Found {len(files)} files in '{folder_path}'")
    print("-" * 50)
    
    for file_path in files:
        filename = file_path.name
        
        # Check if filename contains "DATA"
        if "DATA" in filename:
            # Find the first underscore and replace it with dash
            if "_" in filename:
                new_filename = filename.replace("_", "-", 1)  # Replace only the first occurrence
                new_file_path = file_path.parent / new_filename
                
                print(f"{'[DRY RUN] ' if dry_run else ''}Renaming:")
                print(f"  From: {filename}")
                print(f"  To:   {new_filename}")
                
                if not dry_run:
                    try:
                        file_path.rename(new_file_path)
                        print("  ✓ Success")
                    except Exception as e:
                        print(f"  ✗ Error: {e}")
                        continue
                
                renamed_count += 1
                print()
            else:
                print(f"File contains 'DATA' but no underscore: {filename}")
                print()
        else:
            print(f"Skipping (no 'DATA'): {filename}")
    
    return renamed_count

def main():
    """Main function to handle command line arguments and run the script."""
    if len(sys.argv) < 2:
        print("Usage: python script.py <folder_path> [--execute]")
        print("\nOptions:")
        print("  --execute    Actually perform the renaming (default is dry run)")
        print("\nExample:")
        print("  python script.py /path/to/folder          # Dry run")
        print("  python script.py /path/to/folder --execute # Actually rename files")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("=== DRY RUN MODE ===")
        print("Use --execute flag to actually rename files")
        print()
    else:
        print("=== EXECUTE MODE ===")
        print("Files will be actually renamed!")
        print()
    
    renamed_count = rename_files_with_data(folder_path, dry_run)
    
    print("-" * 50)
    print(f"{'Would rename' if dry_run else 'Renamed'} {renamed_count} file(s)")

if __name__ == "__main__":
    main()

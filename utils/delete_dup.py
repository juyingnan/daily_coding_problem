import os
import re


def find_duplicates(directory):
    # Regex to match the file pattern
    pattern = re.compile(r"(.*?)( \d+)?(\.\w+)$")
    files_dict = {}

    # Walk through the directory and collect files based on the pattern
    for root, _, files in os.walk(directory):
        for file in files:
            match = pattern.match(file)
            if match:
                base_name = match.group(1)
                extension = match.group(3)
                key = f"{base_name}{extension}"
                if key not in files_dict:
                    files_dict[key] = []
                files_dict[key].append(os.path.join(root, file))

    return files_dict


def delete_duplicates(files_dict):
    for key, file_paths in files_dict.items():
        if len(file_paths) > 1:
            # Sort files by the original and then duplicates
            original_file = None
            duplicates = []

            for file_path in file_paths:
                if re.match(rf"{re.escape(key)}$", os.path.basename(file_path)):
                    original_file = file_path
                else:
                    duplicates.append(file_path)

            # Check file sizes
            if original_file and duplicates:
                original_size = os.path.getsize(original_file)
                is_deleted = False
                for duplicate in duplicates:
                    duplicate_size = os.path.getsize(duplicate)
                    if original_size == duplicate_size:
                        # Delete the duplicate file
                        is_deleted = True
                        os.remove(duplicate)
                        print(f"Deleted: {duplicate}")
                    else:
                        print(f"Size mismatch: {duplicate} | {original_size} != {duplicate_size}")

                # Print the original file that is kept
                if is_deleted:
                    print(f"Kept: {original_file}")


if __name__ == "__main__":
    directory = r"H:\iphone 13 pro"  # Replace with your directory path
    files_dict = find_duplicates(directory)
    delete_duplicates(files_dict)

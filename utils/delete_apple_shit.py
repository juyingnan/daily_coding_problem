import os

def delete_ds_store_files(root_dir):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename == '.DS_Store':
                file_path = os.path.join(dirpath, filename)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        directory = r"D:\Downloads"
    else:
        directory = sys.argv[1]
    delete_ds_store_files(directory)

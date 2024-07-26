import os

def process_subfolders(root_folder):
    # Iterate through each subfolder in the root folder
    for subfolder in os.listdir(root_folder):
        subfolder_path = os.path.join(root_folder, subfolder)

        if os.path.isdir(subfolder_path):
            # List all mp4 files in the current subfolder
            mp4_files = [f for f in os.listdir(subfolder_path) if f.endswith('.mp4')]

            # Check the number of mp4 files
            if len(mp4_files) == 0:
                print(f"No MP4 file in subfolder: {subfolder}")
            elif len(mp4_files) > 1:
                print(f"Multiple MP4 files in subfolder: {subfolder}")
            else:
                # If exactly one MP4 file, rename it to the name of the subfolder
                old_file_path = os.path.join(subfolder_path, mp4_files[0])
                new_file_path = os.path.join(subfolder_path, f"{subfolder}.mp4")

                # Rename the file
                os.rename(old_file_path, new_file_path)
                print(f"Renamed {old_file_path} to {new_file_path}")

# Define the root folder path
root_folder_path = '/path/to/your/root/folder'

# Call the function to process subfolders
process_subfolders(root_folder_path)

import os
import chardet


def convert_to_unicode(file_path):
    encodings_to_try = ['gb2312', 'gbk', 'gb18030', 'big5', 'utf-8', 'utf-16']

    content = None
    original_encoding = None
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            original_encoding = encoding
            break
        except UnicodeDecodeError:
            continue

    if content is not None:
        if original_encoding not in ['utf-8', 'utf-16']:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Converted {file_path} from {original_encoding} to utf-8.")
        else:
            print(f"{file_path} is already {original_encoding}.")
    else:
        with open(file_path, 'rb') as f:
            content = f.read()
            detected_encoding = chardet.detect(content)['encoding']
            print(f"Failed to decode {file_path} using common encodings. Detected encoding of {file_path} is"
                  f" {detected_encoding}.")


# List of file extensions to process
extensions = [".srt", ".txt", ".ass", ".sub", ".vtt", ".smi", ".ssa"]

# Directory containing your text files
directory = r'C:\Users\bunny\Desktop\TXTS'

# Replace the simple directory listing with recursive traversal
for root, dirs, files in os.walk(directory):
    for filename in files:
        if any(filename.endswith(ext) for ext in extensions):
            file_path = os.path.join(root, filename)
            convert_to_unicode(file_path)

import os

def list_directory_tree(root_dir):
    """Return a string representation of the directory tree, limited to .py, .ini, and .md files."""
    tree = []
    for root, dirs, files in os.walk(root_dir):
        level = root.replace(root_dir, '').count(os.sep)
        indent = ' ' * 4 * (level)
        tree.append(f'{indent}{os.path.basename(root)}/')
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            if f.endswith('.py') or f.endswith('.ini') or f.endswith('.md'):
                tree.append(f'{sub_indent}{f}')
    return '\n'.join(tree)

def read_file_content(file_path):
    """Read file content with multiple encoding attempts."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

def flatten_folder(root_dir, output_file):
    """Create a flat text representation of the folder structure and file contents."""
    with open(output_file, 'w', encoding='utf-8') as out_f:
        # Write the directory tree
        out_f.write("Directory Tree:\n")
        out_f.write(list_directory_tree(root_dir))
        out_f.write("\n\n")
        
        # Walk through the directory and write each file's content
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith('.py') or file.endswith('.ini') or file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    out_f.write(f"File: {file_path}\n")
                    content = read_file_content(file_path)
                    out_f.write(content)
                    out_f.write("\n\n")

# Usage
root_directory = r'C:\Users\yingnanju\source\repos\daily_coding_problem'  # Use raw string to handle backslashes
output_filename = 'flat_text_representation.txt'
flatten_folder(root_directory, output_filename)
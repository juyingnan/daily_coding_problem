import os
import re
import requests


def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, ' ')
    return filename.strip()


def get_movie_id(filename):
    match = re.search(r'([a-zA-Z]{2,6})-? ?(\d{2,5})', filename)
    if match:
        return f'{match.group(1).upper()}-{match.group(2)}'
    return None


def get_movie_info(movie_id):
    search_url = f'http://URL/cn/vl_searchbyid.php?keyword={movie_id}'
    try:
        response = requests.get(search_url, timeout=10)
        response.encoding = 'utf-8'
        title_match = re.search(r'<title>([a-zA-Z]{1,6}-\d{1,5}.+?) - URL</title>', response.text)
        if not title_match:
            # Try again with this format # title="{movie_id} ">
            # print(f'Failed to find title for {movie_id}. Trying again with a different format.')
            title_match = re.search(r'title="([a-zA-Z]{1,6}-\d{1,5}.+?)">', response.text)
        if title_match:
            title = title_match.group(1)
            sanitized_title = sanitize_filename(title)
            if not sanitized_title.lower().startswith(movie_id.lower()):
                print('id mismatch, double check the result:')
            return sanitized_title

    except requests.RequestException as e:
        print(f'Error fetching info for {movie_id}: {e}')
    print(f'Failed to find title for {movie_id}.')
    return None


def main():
    folder_path = r'ROOTPATH'
    rename_list = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(('.mp4', '.mkv', '.avi', '.wmv', '.srt', '.ssa', '.ass', '.vtt')):
                movie_id = get_movie_id(file)
                if movie_id:
                    new_name = get_movie_info(movie_id)
                    if new_name:
                        if '-C' in file or '-UC' in file:
                            new_name = new_name.replace(movie_id, movie_id + 'C')
                            movie_id = movie_id + 'C'
                        if '-4k' in file or '-4K' in file:
                            new_name = new_name.replace(movie_id, movie_id + '-4k')
                            movie_id = movie_id + '-4k'
                        old_file_path = file
                        new_file_path = new_name + os.path.splitext(file)[1]
                        rename_list.append((old_file_path, new_file_path))
                        print(new_file_path)

    with open(os.path.join(folder_path, 'rename_list.txt'), 'w', encoding='utf-16') as f:
        for old_name, new_name in rename_list:
            f.write(f'{old_name} | {new_name}\n')

    print('Done! The rename list has been saved to "rename_list.txt".')


if __name__ == '__main__':
    main()

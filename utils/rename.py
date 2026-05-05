import json
import os
import re
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


MOVIE_ID_RE = re.compile(r'([a-zA-Z]{2,6})-? ?(\d{2,5})')
INVALID_FILENAME_TRANS = str.maketrans({c: ' ' for c in '<>:"/\\|?*'})

def load_sources_config():
    cfg_path = os.environ.get(
        "RENAME_SOURCES_CONFIG",
        os.path.join(os.path.dirname(__file__), "rename_sources_config.json"),
    )
    if not os.path.isfile(cfg_path):
        raise RuntimeError(
            "Sources config not found. Set RENAME_SOURCES_CONFIG or create rename_sources_config.json."
        )
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def sanitize_filename(filename):
    return filename.translate(INVALID_FILENAME_TRANS).strip()


def get_movie_id(filename):
    match = MOVIE_ID_RE.search(filename)
    if match:
        return f'{match.group(1).upper()}-{match.group(2)}'
    return None


def get_movie_id_source1(movie_id, driver, cfg):
    src_cfg = cfg.get("source1", {})
    search_url = src_cfg.get("search_url")
    if not search_url:
        logging.error("source1.search_url is missing in config")
        return ""
    search_url = search_url.format(movie_id=movie_id)
    try:
        driver.get(search_url)
        # Wait for content to load (Cloudflare challenge)
        title_class = src_cfg.get("title_class")
        if not title_class:
            logging.error("source1.title_class is missing in config")
            return ""
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CLASS_NAME, title_class)
            )
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        title_text = soup.title.get_text(strip=True) if soup.title else ''
        block_tokens = src_cfg.get("block_title_keywords", [])
        if any(token in title_text for token in block_tokens):
            logging.warning(f"Block page detected for {movie_id}")
            return ""
        title_selector = src_cfg.get("title_selector")
        if not title_selector:
            logging.error("source1.title_selector is missing in config")
            return ""
        titles = soup.select(title_selector)
        for title in titles:
            strong_tag = title.find('strong')
            if strong_tag and strong_tag.text.lower() == movie_id.lower():
                content = title.get_text(strip=True).replace(strong_tag.text, '').strip()
                for token in src_cfg.get("strip_tokens", []):
                    content = content.replace(token, "")
                content = content.strip()
                return f"{strong_tag.text.upper()} {content}"
        logging.warning(f"Title index not found for {movie_id}")
        return ""
    except Exception as e:
        logging.error(f"Error fetching {movie_id} from source1: {e}")
        return ""


def get_movie_id_source2(movie_id, driver, cfg):
    src_cfg = cfg.get("source2", {})
    search_url = src_cfg.get("search_url")
    if not search_url:
        logging.error("source2.search_url is missing in config")
        return ""
    search_url = search_url.format(movie_id=movie_id)
    driver.get(search_url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    title_tag = soup.find('title')
    if title_tag:
        suffix = src_cfg.get("title_suffix", "")
        title_text = title_tag.text.replace(suffix, '').strip()
        return f"{movie_id.upper()} {title_text}"
    logging.warning(f"Title not found for {movie_id}")
    return ""


def get_movie_info(movie_id, driver, cfg, source='source1'):
    try:
        if source == 'source1':
            title_text = get_movie_id_source1(movie_id, driver, cfg)
        elif source == 'source2':
            title_text = get_movie_id_source2(movie_id, driver, cfg)
        else:
            logging.error(f'Unknown source: {source}')
            return None

        if not title_text:
            logging.warning(f'Failed to find title for {movie_id}.')
            return None
        sanitized_title = sanitize_filename(title_text)
        if not sanitized_title.startswith(movie_id.upper()):
            logging.warning('id mismatch, double check the result:')
        return sanitized_title

    except Exception as e:
        logging.error(f'Error fetching info for {movie_id}: {e}')
    logging.warning(f'Failed to find title for {movie_id}.')
    return None


def main(driver, sources_cfg, sleep_duration=5):
    folder_path = r'E:\Downloads\TEMP\TEMP'
    rename_list = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(('.mp4', '.mkv', '.avi', '.wmv', '.srt', '.ssa', '.ass', '.vtt')):
                movie_id = get_movie_id(file)
                if movie_id:
                    new_name = get_movie_info(movie_id, driver, sources_cfg, source='source1')
                    time.sleep(sleep_duration)
                    if new_name:
                        final_movie_id = movie_id
                        if '-C' in file or '-UC' in file:
                            final_movie_id = f"{final_movie_id}C"
                        if '-4k' in file or '-4K' in file:
                            final_movie_id = f"{final_movie_id}-4k"
                        if final_movie_id != movie_id:
                            new_name = new_name.replace(movie_id, final_movie_id)
                            movie_id = final_movie_id
                        old_file_path = file
                        new_file_path = new_name + os.path.splitext(file)[1]
                        rename_list.append((old_file_path, new_file_path))
                        logging.info(f"Renamed: {old_file_path} -> {new_file_path}")

    with open(os.path.join(folder_path, 'rename_list.txt'), 'w', encoding='utf-16') as f:
        for old_name, new_name in rename_list:
            f.write(f'{old_name} | {new_name}\n')

    logging.info('Done! The rename list has been saved to "rename_list.txt".')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Initialize Chrome driver with headless option
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    sources_cfg = load_sources_config()

    try:
        main(driver, sources_cfg)
    finally:
        driver.quit()

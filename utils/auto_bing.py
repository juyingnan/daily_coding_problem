import random
import webbrowser
import pyautogui
import time
from pathlib import Path

# Timing tweaks
BROWSER_STARTUP = 5

BETWEEN_SEARCHES = (60, 70)  # 5-6 minutes
MOUSE_CHECK_INTERVAL = 15

SEARCH_LIMIT = 30


def activate_and_clear_existing_search():
    pyautogui.write('a', interval=0.05)
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)
    pyautogui.press('delete')
    time.sleep(0.1)

def perform_search(search_terms):
    # Open Bing in the default browser
    webbrowser.open("https://www.bing.com")

    # Wait for the browser to open
    time.sleep(BROWSER_STARTUP)

    for idx, term in enumerate(search_terms):
        if idx == 0:
            # First search starts from the Bing homepage, so focus the input once.
            pyautogui.click(600, 400)
            time.sleep(2 + 2 * random.random())
        else:
            # On results pages, typing activates the existing search box.
            activate_and_clear_existing_search()

        # Type the search term
        pyautogui.typewrite(term.lower(), interval=0.1)

        # Wait for a few seconds to mimic human behavior
        time.sleep(2 + 2 * random.random())

        # Press Enter to search
        pyautogui.press('enter')

        # Wait for 5 minutes + a small random offset before the next iteration
        total_wait_time = random.randint(*BETWEEN_SEARCHES)
        elapsed_time = 0

        while elapsed_time < total_wait_time:
            # Move the mouse a few pixels from its current position to keep the screen active
            current_x, current_y = pyautogui.position()
            new_x = current_x + random.randint(-10, 10)
            new_y = current_y + random.randint(-10, 10)
            pyautogui.moveTo(new_x, new_y, duration=1)

            # Wait before moving the mouse again
            wait_time = min(MOUSE_CHECK_INTERVAL + random.randint(0, 10), total_wait_time - elapsed_time)
            time.sleep(wait_time)
            elapsed_time += wait_time


if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    pokemon_file = script_dir / 'pokemon_name_list.txt'
    
    if not pokemon_file.exists():
        print(f"Error: File not found: {pokemon_file}")
        exit(1)
    
    # List of Pokémon names
    with open(pokemon_file, 'r') as file:
        pokemon_names = file.read().splitlines()

    # Randomly shuffle the list of names
    random.shuffle(pokemon_names)

    # Select random Pokémon names for the search
    search_names = pokemon_names[:SEARCH_LIMIT]

    # Perform the searches
    perform_search(search_names)

import random
import webbrowser
import pyautogui
import time
from pathlib import Path

# Configuration - adjust these based on your screen
SEARCH_BOX_X = 600
SEARCH_BOX_Y = 400

# Timing tweaks
BROWSER_STARTUP = 5
CLICK_TO_TYPE_DELAY = (2, 4)
TYPE_TO_ENTER_DELAY = (2, 4)
BETWEEN_SEARCHES = (300, 360)  # 5-6 minutes
MOUSE_CHECK_INTERVAL = 30

SEARCH_LIMIT = 30


def perform_search(search_terms):
    # Open Bing in the default browser
    webbrowser.open("https://www.bing.com")

    # Wait for the browser to open
    time.sleep(BROWSER_STARTUP)

    for idx, term in enumerate(search_terms, 1):
        print(f"Search {idx}/{len(search_terms)}: {term}")
        
        try:
            # Click on the search box
            pyautogui.click(SEARCH_BOX_X, SEARCH_BOX_Y)

            # Add a slight delay to ensure the search box is focused
            time.sleep(random.uniform(*CLICK_TO_TYPE_DELAY))

            # Clear search box with backspace
            for _ in range(20):
                pyautogui.press('backspace')
            time.sleep(0.1)

            # Type the search term
            pyautogui.typewrite(term.lower(), interval=0.1)

            # Wait before pressing Enter
            time.sleep(random.uniform(*TYPE_TO_ENTER_DELAY))

            # Press Enter to search
            pyautogui.press('enter')

            # Wait for 5-6 minutes before the next iteration
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
                
        except Exception as e:
            print(f"Error during search: {e}")
            time.sleep(5)
            continue


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

import random
import webbrowser
import pyautogui
import time


def perform_search(search_terms):
    # Open Bing in the default browser
    webbrowser.open("https://www.bing.com")

    # Wait for the browser to open
    time.sleep(5)  # Adjust this delay based on your browser's startup time

    for term in search_terms:
        # Click on the search box (you might need to adjust coordinates based on your screen resolution)
        pyautogui.click(600, 400)

        # Add a slight delay to ensure the search box is focused
        time.sleep(2 + 2 * random.random())

        # Type the search term
        pyautogui.typewrite(term.lower(), interval=0.1)

        # Wait for a few seconds to mimic human behavior
        time.sleep(2 + 2 * random.random())

        # Press Enter to search
        pyautogui.press('enter')

        # Wait for 5 minutes + a small random offset before the next iteration
        total_wait_time = 300 + random.randint(0, 60)
        elapsed_time = 0

        while elapsed_time < total_wait_time:
            # Move the mouse a few pixels from its current position to keep the screen active
            current_x, current_y = pyautogui.position()
            new_x = current_x + random.randint(-10, 10)
            new_y = current_y + random.randint(-10, 10)
            pyautogui.moveTo(new_x, new_y, duration=1)

            # Wait for 30 seconds before moving the mouse again
            wait_time = min(30 + 5 * random.random(), total_wait_time - elapsed_time)
            time.sleep(wait_time)
            elapsed_time += wait_time

        # Return to Bing homepage for the next search
        # webbrowser.open("https://www.bing.com")
        # time.sleep(5 + 2 * random.random())


if __name__ == "__main__":
    # List of Pokémon names
    with open('pokemon_name_list.txt', 'r') as file:
        pokemon_names = file.read().splitlines()

    # Randomly shuffle the list of names
    random.shuffle(pokemon_names)

    # Select 30 random Pokémon names for the search
    search_names = pokemon_names[:30]

    # Perform the searches
    perform_search(search_names)

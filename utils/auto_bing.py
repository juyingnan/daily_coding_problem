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
        time.sleep(1)

        # Type the search term
        pyautogui.typewrite(term.lower(), interval=0.1)

        # Press Enter to search
        pyautogui.press('enter')

        # Wait for a few seconds before the next search to mimic human behavior
        # random seconds between 3 and 5
        time.sleep(5 + 2 * random.random())

        # Return to Bing homepage for the next search
        webbrowser.open("https://www.bing.com")
        time.sleep(5 + 2 * random.random())  # Adjust this delay based on how quickly the homepage loads


if __name__ == "__main__":
    # List of Pokémon names
    pokemon_names = [
        "Pikachu", "Bulbasaur", "Charmander", "Squirtle", "Jigglypuff",
        "Meowth", "Psyduck", "Snorlax", "Eevee", "Vaporeon",
        "Jolteon", "Flareon", "Porygon", "Togepi", "Mareep",
        "Espeon", "Umbreon", "Leafeon", "Glaceon", "Sylveon",
        "Chikorita", "Cyndaquil", "Totodile", "Pichu", "Cleffa",
        "Igglybuff", "Togetic", "Giratina", "Gengar", "Shedinja"
    ]

    # Perform the searches
    perform_search(pokemon_names)

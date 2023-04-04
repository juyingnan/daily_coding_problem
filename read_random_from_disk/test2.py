# Read the text of "The Great Gatsby" from a file
with open("great_gatsby.txt", "r") as f:
    text = f.read()

# Define the number of characters between each number
number_interval = 100

# Define the number of characters between each line break
line_break_interval = 4000

# Initialize the file content and character count
file_content = ""
char_count = 0

# Insert numbers every 100 characters
for i, char in enumerate(text):
    # Add the character to the file content
    file_content += char
    char_count += 1
    number_length = 0
    # Insert a number every 100 characters
    if char_count % number_interval == 0:
        file_content += "__" + str(char_count) + "__"
        # Increment the character count to account for the added number
        number_length = len(str(char_count)) + 4
        char_count += number_length
    if (char_count - number_length) % line_break_interval == 0:
        file_content += "\n"
        # Increment the character count to account for the added line break
        char_count += 1

# Write the file content to a file
with open("great_gatsby_file.txt", "w") as f:
    f.write(file_content)

def read_file(filename):
    with open(filename, 'r') as file:
        return file.read()

filename = 'random_file.txt'  # replace with the name of your file
text = read_file(filename)
position = 0
default_n = 4096

while True:
    n = input("Enter the number of characters to display (default is 4k): ")
    if not n:
        n = default_n
    else:
        n = int(n)
    if n == -1:
        break
    next_text = text[position:position+n]
    next_preview = text[position+n:position+n+20]
    print(next_text)
    print("Preview to the next 20 characters:", next_preview)
    position += n
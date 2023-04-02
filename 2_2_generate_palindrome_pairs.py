def is_palindrome(word):
    return word == word[::-1]


def palindrome_pairs(words):
    result = []

    for i, word1 in enumerate(words):
        for j, word2 in enumerate(words):
            if i != j and is_palindrome(word1 + word2):
                result.append([i, j])
    return result


if __name__ == '__main__':
    print(palindrome_pairs(["code", "edoc", "da", "d"]))
    print(palindrome_pairs(["abc", "cba", "xy", "yx", "x", "xx", "yy", ""]))
    print(palindrome_pairs(["bat", "tab", "cat"]))

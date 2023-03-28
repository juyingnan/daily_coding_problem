# The "find anagram indices" problem involves finding all starting indices of the anagrams of a given pattern in a
# larger string. An anagram is a word or phrase formed by rearranging the letters of a different word or phrase,
# using all the original letters exactly once.
#
# The problem can be formally stated as follows: given a string s and a pattern p, find all starting indices of the
# anagrams of p in s. The output should be a list of integers representing the starting indices of the anagrams,
# sorted in ascending order.
#
# For example, given the string s = "cbaebabacd" and the pattern p = "abc", the output should be [0, 6],
# since the anagrams of "abc" in "cbaebabacd" are "cba" and "bac", which start at indices 0 and 6 respectively.
#
# Note that the input strings may contain only lowercase English letters, and the length of the pattern p should be
# less than or equal to the length of s.

from collections import Counter


def find_anagram_indices(s: str, p: str) -> list[int]:
    """
    Find all starting indices of anagrams of pattern p in string s.
    """
    p_count = Counter(p)
    s_count = Counter(s[:len(p)])
    indices = []
    for i in range(len(p), len(s)):
        if p_count == s_count:
            indices.append(i - len(p))
        s_count[s[i - len(p)]] -= 1
        if s_count[s[i - len(p)]] == 0:
            del s_count[s[i - len(p)]]
        s_count[s[i]] += 1
    if p_count == s_count:
        indices.append(len(s) - len(p))
    return indices

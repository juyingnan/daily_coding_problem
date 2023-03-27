# given an array of integers, return a new array such that each element at index i of the new array is the product of
# all the numbers in the original array except the one at i

# LIMIT: do division

# GPT better solution

# This solution has a time complexity of O(n), where n is the length of the input array, and a space complexity of
# O(n), since it creates a new output array of the same size as the input array.
#
# The solution uses two passes through the input array. In the first pass, it calculates the product of all elements
# to the left of i and stores it in the output array. In the second pass, it calculates the product of all elements to
# the right of i and multiplies it by the existing product stored in the output array. The final output array contains
# the product of all elements in the input array except the one at i.
def product_of_others(arr):
    n = len(arr)
    output = [1] * n
    left_product = 1
    right_product = 1

    # Calculate the product of all elements to the left of i
    for i in range(n):
        output[i] *= left_product
        left_product *= arr[i]

    # Calculate the product of all elements to the right of i
    for i in range(n - 1, -1, -1):
        output[i] *= right_product
        right_product *= arr[i]

    return output


# test
print(product_of_others([1, 2, 3, 4, 5]))

# [1,2,3,4,5]
#  * * * * *
#  1 1 1 1 1
#  * * * * *
#  2 2 2 2 3
#  * * * * *
#  3 3 3 3 3
#  * * * * *
#  4 4 4 4 4
#  * * * * *
#  5 5 5 5 5
#
# without x themselves:
# [1,2,3,4,5]
#  * * * * *
#    1 1 1 1
#  * * * * *
#  2   2 2 3
#  * * * * *
#  3 3   3 3
#  * * * * *
#  4 4 4   4
#  * * * * *
#  5 5 5 5

# the question was changed to product 2 triangle

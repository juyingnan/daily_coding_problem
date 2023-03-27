# Given an array of integers, find the contiguous subarray with the largest sum.

# Your solution should have a time complexity of O(n), where n is the length of the input array.

def max_subarray_sum(arr):
    max_sum = arr[0]
    current_sum = arr[0]
    for i in range(1, len(arr)):
        current_sum = max(arr[i], current_sum + arr[i])
        max_sum = max(max_sum, current_sum)
    return max_sum


# The function works as follows:
#
# 1. We initialize two variables max_sum and current_sum to the first element of the input array.
# 2. We loop through the remaining elements of the array, starting from index 1.
# 3. At each index i, we update current_sum to be the maximum of the current element and the sum of the current element
# and current_sum.
# 4. We update max_sum to be the maximum of max_sum and current_sum.
# 5. We return max_sum.
# This algorithm works because at each index i, we are considering the maximum sum of a subarray that ends at index i.
# If the current element is greater than the sum of the current element and the previous subarray, then the subarray
# should start from the current element. Otherwise, the subarray should continue from the previous subarray.


def max_subarray_sum_wrapup(arr):
    max_sum = arr[0]
    current_sum = arr[0]
    for i in range(1, len(arr)):
        current_sum = max(arr[i], current_sum + arr[i])
        max_sum = max(max_sum, current_sum)

    # Check for maximum subarray sum with wrapping around
    arr_sum = sum(arr)
    min_sum = arr[0]
    current_sum = arr[0]
    for i in range(1, len(arr)):
        current_sum = min(arr[i], current_sum + arr[i])
        min_sum = min(min_sum, current_sum)

    return max(max_sum, arr_sum - min_sum)

# The function now checks for the maximum subarray sum without wrapping around using the original Kadane's algorithm.
# Then, it calculates the sum of the entire array arr_sum, and checks for the maximum subarray sum with wrapping around
# by finding the minimum subarray sum. Finally, it returns the maximum of the two sums.

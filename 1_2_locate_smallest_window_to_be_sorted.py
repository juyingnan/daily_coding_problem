# given an array of integers that are out of order, determine the bounds of the smallest window that must be sorted
# in order for the entire array to be sorted. For example, given [3,7,5,6,9], you should return (1,3)

def smallest_window(arr):
    n = len(arr)
    left_bound = n - 1
    right_bound = 0

    # Find the right bound of the smallest unsorted subarray
    max_seen = float('-inf')
    for i in range(n):
        if arr[i] < max_seen:
            right_bound = i
        else:
            max_seen = arr[i]

    # Find the left bound of the smallest unsorted subarray
    min_seen = float('inf')
    for i in range(n - 1, -1, -1):
        if arr[i] > min_seen:
            left_bound = i
        else:
            min_seen = arr[i]

    if left_bound >= right_bound:
        return None

    return left_bound, right_bound

# This solution has a time complexity of O(n) and a space complexity of O(1).
#
# The solution works as follows:
#
# * We first iterate over the array from left to right to find the right bound of the smallest unsorted subarray. We
# keep track of the maximum element seen so far and update the right bound whenever we encounter an element that is
# less than the maximum seen so far.
# * We then iterate over the array from right to left to find the left bound of the smallest unsorted subarray.
# We keep track of the minimum element seen so far and update the left bound whenever we encounter an element that
# is greater than the minimum seen so far.
# * If the left bound is greater than or equal to the right bound, the array is already sorted, and we return None.
# * Otherwise, we return a tuple of the left and right bounds of the smallest unsorted subarray.
#

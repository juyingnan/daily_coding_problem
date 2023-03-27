# O(nlogn) time complexity

def smaller_numbers(nums):
    result = [0] * len(nums)
    pairs = list(enumerate(nums))

    def merge_sort(pairs):
        if len(pairs) <= 1:
            return pairs

        mid = len(pairs) // 2
        left = merge_sort(pairs[:mid])
        right = merge_sort(pairs[mid:])

        i = j = 0
        while i < len(left) or j < len(right):
            if j == len(right) or (i < len(left) and left[i][1] <= right[j][1]):
                result[left[i][0]] += j
                pairs[i + j] = left[i]
                i += 1
            else:
                pairs[i + j] = right[j]
                j += 1

        return pairs

    merge_sort(pairs)
    return result


# another method using bisect
from bisect import bisect_left


def smaller_numbers_bisect(nums):
    result = []
    sorted_nums = []
    for num in reversed(nums):
        index = bisect_left(sorted_nums, num)
        result.append(index)
        sorted_nums.insert(index, num)
    return result[::-1]

# # Step 1: Process 1
# num = 1
# index = bisect_left(sorted_nums, num)  # index = 0
# result.append(index)  # result = [0]
# sorted_nums.insert(index, num)  # sorted_nums = [1]
#
# result: [0]
# sorted_nums: [1]
#
# # Step 2: Process 6
# num = 6
# index = bisect_left(sorted_nums, num)  # index = 1
# result.append(index)  # result = [0, 1]
# sorted_nums.insert(index, num)  # sorted_nums = [1, 6]
#
# result: [0, 1]
# sorted_nums: [1, 6]
#
# # Step 3: Process 2
# num = 2
# index = bisect_left(sorted_nums, num)  # index = 0
# result.append(index)  # result = [0, 1, 1]
# sorted_nums.insert(index, num)  # sorted_nums = [1, 2, 6]
#
# result: [0, 1, 1]
# sorted_nums: [1, 2, 6]
#
# # Step 4: Process 5
# num = 5
# index = bisect_left(sorted_nums, num)  # index = 2
# result.append(index)  # result = [0, 1, 1, 2]
# sorted_nums.insert(index, num)  # sorted_nums = [1, 2, 5, 6]
#
# result: [0, 1, 1, 2]
# sorted_nums: [1, 2, 5, 6]
#
# Final result: [2, 1, 1, 0]

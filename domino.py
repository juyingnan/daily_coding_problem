# you can write to stdout for debugging purposes, e.g.
# print("this is a debug message")

def solution(A):
    # Implement your solution here

    # using a graph to represents dominos
    graph = dict()

    for i in range(0, len(A)):
        a = A[i]

        if a not in graph:
            graph[a] = [i // 2]
        else:
            graph[a].append(i // 2)

    # try BFS to solve the connected dominos
    # build a visited list
    visited = [False] * (len(A) // 2)
    connected = []

    for i in range(len(A) // 2):
        if not visited[i]:
            component = []
            temp = [i]
            visited[i] = True

            # pop. BFS
            while (len(temp) > 0):
                index = temp.pop(0)
                component.append(index)
                left = A[index * 2]
                right = A[index * 2 + 1]

                for g in graph[left]:
                    if not visited[g]:
                        temp.append(g)
                        visited[g] = True

                # same for right
                for g in graph[right]:
                    if not visited[g]:
                        temp.append(g)
                        visited[g] = True

            connected.append(component)

    # for each connected component, find the minimum number of removals
    total_removal = 0

    # Loop through component in the list of connected components
    for component in connected:
        # dictionary to store the count
        counts = {}
        for index in component:
            left = A[index * 2]
            right = A[index * 2 + 1]

            if left not in counts:
                counts[left] = 1
            else:
                counts[left] += 1

            if right not in counts:
                counts[right] = 1
            else:
                counts[right] += 1

        # maximum count of any number in the current connected component
        max_count = max(counts.values())
        # the initial minimum removals
        min_removals = len(component) * 2 - max_count

        # check if swapping any domino decreases the minimum removals
        for index in component:
            left = A[index * 2]
            right = A[index * 2 + 1]
            # dictionary to store the swapped counts
            swap_left = counts[right] if right in counts else 0
            swap_right = counts[left] if left in counts else 0
            swap = {left: swap_left, right: swap_right}
            # maximum swapped count
            max_count = max(swap.values())
            min_removals = min(min_removals, len(component) * 2 - max_count)

        total_removal += min_removals // 2

    return total_removal

dominoes = [2, 4, 1, 3, 4, 6, 2, 4, 1, 6]
print(solution(dominoes))  # Output: 3


def sum_to(n: int) -> int:
    total = 0
    i = 0
    while i < n:
        total = total + i * 3 - i // 2
        i = i + 1
    return total


print(sum_to(50000000))

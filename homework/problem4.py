def func(lst, k):
    if k < 0 or k > len(lst):
        return None
    lst1 = sorted(lst[:k], reverse=True) + lst[k:]
    lst2 = lst[:k] + sorted(lst[k:], reverse=True)
    lst3 = sorted(lst, reverse=True)
    return lst1, lst2, lst3


lst = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
lst1, lst2, lst3 = func(lst, 5)
print(lst1, lst2, lst3, sep='\n')





#len(iterable) -> int 
#sum(iterable)
lst=[10,20,6,40,50,2,30,40,50]

#min(iterable) -> value
small=lst[0]
for i in lst[1::]:
    if i<small:
        small=i

print("Min val is : ",small)
print("Min val is : ",min(lst))

s="welcome"
print("Data is : ",s)
print("Min is : ",min(s))



'''
max(iterable)
all(iterable)
any(iterable)
'''







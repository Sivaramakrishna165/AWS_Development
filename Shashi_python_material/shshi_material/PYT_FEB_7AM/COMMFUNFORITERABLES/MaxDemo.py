

#len(iterable) -> int 
#sum(iterable)
#min(iterable) -> value
lst=[10,20,6,40,50,2,30,40,50]

big=lst[0]
for i in lst[1::]:
    if i>big:
       big=i

print("Max val is : ",big)
print("Max val is : ",max(lst))

s="welcome"
print("Data is : ",s)
print("Max is : ",max(s))


'''
max(iterable)
all(iterable)
any(iterable)
'''








#len(iterable) -> int
s="sai"
print("String : ",s)
nc=len(s)
print("No.of.char is : ",nc)
print("=================")

lst=[10,20,30,40,50,60]
print("List : ",lst)
ni=len(lst)
print("no.of.Objects : ",ni)
print("=================")

#sum(iterable) -> int

lst=[10,20,30,40]
print("List : ",lst)
s=0
for i in lst:
    s=s+i
print("sum is : ",s)
print("sum is : ",sum(lst))
# print( sum(10,20) ) Error

#min(iterable) -> int
#min(arg1,arg2,.....)

t=(10,2,30,40)
print("tuple : ",t)
small=t[0]
for i in t:
    if i<small:
        small=i
print("min : ",small)
print("==============")
print("Min : ",min(t))
print("===============")

s="bcdaef"
print("String : ",s)
print("min char : ",min(s))
print("===================")

print( min(10,20,30,3,40,50) )

#max(iterable) -> int
#max(arg1,arg2,......)
s={20,30,40,50,10,120}
print("set : ",s)
print("biggest : ", max(s) )
print("=====================")

print("max char : ",max("welcome"))
print("max : ",max(40,30,20,10))

#all(iterable) -> int
#any(iterable) -> int 

















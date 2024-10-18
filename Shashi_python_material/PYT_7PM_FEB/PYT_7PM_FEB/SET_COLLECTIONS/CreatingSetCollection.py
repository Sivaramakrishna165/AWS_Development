#set( ) -> set object 
s1=set()
print("Type is : ",type(s1))
print("Set Object : ",s1)
print("========================")

s2={10,12.12,None,10,"Shashi"}
print("Type is : ",type(s2))
print("Data is : ",s2)
print("========================")

#set(iterable) -> set

lst=[10,20,30,30,40,40,50,20,10]
print("List : ",lst)
'''
lst2=[]
for i in lst:
    if i not in lst2:
        lst2.append(i)
print("List 2 : ",lst2)  '''

s=set(lst)
print("Set : ",s)
print("========================")

s="welcome"
print("string : ",s)
st=set(s)
print("Result is : ",st)

















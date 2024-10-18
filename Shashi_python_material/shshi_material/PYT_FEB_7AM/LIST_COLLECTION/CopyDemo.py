
#L.copy( ) -> shallow copy of list
#Ref copy vs shallow copy

a=[10,20,30]
b=a
print("List a : ",a)
print("List b : ",b)
a[1]=99
print("After Modification ")
print("List a : ",a)
print("List b : ",b)
print("==============")

c=[1.1,2.2,3.3]
d=c.copy()
print("List c : ",c)
print("List d : ",d)
c[1]=9.9
print("After Modification ")
print("List c : ",c)
print("List d : ",d)









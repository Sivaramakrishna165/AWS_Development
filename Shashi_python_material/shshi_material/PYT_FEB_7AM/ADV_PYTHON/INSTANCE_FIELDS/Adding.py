class Test:
    pass

#calling
t=Test()

#Adding an instance field from outside of the class
#objectref.variable=value
t.x=10
print("x : ",t.x)

#Modify the instance field From outside of the class
t.x=99
print("x : ",t.x)

#deleting an instance field
del t.x
print("x : ",t.x) #AttributeError







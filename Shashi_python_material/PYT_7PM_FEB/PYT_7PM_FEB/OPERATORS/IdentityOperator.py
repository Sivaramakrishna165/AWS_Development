



''' identity operator
      are used to compare ids of the objects
          "is"  : It will returns True iff ids of both objects
                            are Same

                            object1 is object2
                            
          "is not" If will returns True iff ids of both
          Objects are not same

                    object1 is not object2

'''
x=10
y=20
print("id(x) ? : ",id(x))
print("id(y) ? : ",id(y))
print(id(x)==id(y)) #False
print(x is y) #False

z=x
print("id(z) ? : ",id(z))
print(x is z) #True

print(x is not y) #True


















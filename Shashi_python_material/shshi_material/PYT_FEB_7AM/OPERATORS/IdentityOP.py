
''' identity operators
      is - Returns True iff ids of both objects are same
                       Syn: object1 is object2
      is not :
          - Returns True iff ids of both objects are not same
                    Syn: object1 is not object2'''


x=10
y=20

print("id(x) ? ",id(x))
print("id(y) ? ",id(y))





print("id(x) and id(y) are same ? : ",id(x)==id(y))
print("id(x) and id(y) are same ? : ",x is y)

print("id(x) and id(y) are not same ? : ",x is not y)


a=10
b=a #Ref.copy
print(a is b)











































class Sample:
    pass

#calling
s=Sample()

#adding an instance field
s.x=10
print("After Adding : ",s.x)

#changing the value of instance field
s.x=99
print("After modification : ",s.x)

#deleting an instance field
del s.x
print("After deleting ")
print("x val is : ",s.x)

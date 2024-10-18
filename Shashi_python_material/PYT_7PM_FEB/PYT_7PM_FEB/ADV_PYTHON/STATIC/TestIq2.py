
class Sample:
    pass

#calling
s=Sample()

#adding an static field
Sample.x=10
print("After Adding : ",Sample.x)

#changing the value of static field
Sample.x=99
print("After modification : ",Sample.x)

#deleting an static field
del Sample.x
print("After deleting ")
print("x val is : ",Sample.x)

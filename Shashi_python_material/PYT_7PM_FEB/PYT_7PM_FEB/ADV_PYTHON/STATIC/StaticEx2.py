
class Sample:
    x=10 #static variable

''' calling '''
#print("x val is : ",x) NE
print("x val is : ",Sample.x)
s=Sample()
print("x val is : ",s.x)

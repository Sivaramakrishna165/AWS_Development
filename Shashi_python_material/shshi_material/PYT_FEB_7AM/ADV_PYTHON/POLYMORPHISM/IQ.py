
class Shashi:
    def __init__(self):
        self.name="Mr.Kumar"
        self.job="Digital IT Coach "

    def __str__(self):
        return self.name+" "+self.job

#calling
#print(dir(Shashi))
    
s=Shashi()
print(s)

t=(10,20,30,40)
lst=list(t)
print(lst)

'''Note: While printing the reference variable
PVM Internally calls __str__(self) method
from object class,which is used to print the hashcode

If u want display other than hashcode then
we have to override __str__(self) from object class '''








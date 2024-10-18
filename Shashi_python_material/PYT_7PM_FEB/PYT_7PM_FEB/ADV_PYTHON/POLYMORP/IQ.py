
class Shashi:
    def __init__(self):
        self.name="Shashi"
        self.job="Digital IT Coach"

    def __str__(self):
        return self.name+" As "+self.job

''' calling '''
s=Shashi()
print("s : ",s)

print("=================")
d={"sno":101,"sname":"ramesh"}
print("d : ",d)

'''Note: while printing the reference variable PVM internally
calls __str__(self) method from object class.It is always
used to return hashcode of the object.

If u want other than the hashcode then we have to
override __str__(self) from object class '''







class Sample:
    def method1(self):
        self.x=10 #instance field
        print("Mtd-1 x val is : ",self.x)

#calling
s=Sample()
s.method1()
print("From outside of the class")
#print("x val is : ",x)
print("x val is : ",s.x)

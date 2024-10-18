
class Sample:
    def method1(self):
        print("mtd-1 of Sample")
        print("self : \n",self)
        print("================")
    
    def method2(self):
        print("mtd-2 of Sample")
        print("self : \n ",self)
        print("=================")

#calling
s=Sample()
print("From outside of the class")
print("hcode is : \n ",s)
print("======================")

s.method1()
s.method2()


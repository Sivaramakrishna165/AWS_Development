
class Sample:
    def method1(self,x):
        print("mtd-1 of Sample")
        print("self : \n",self)
        print("x val is : ",x)
        print("======================")

    def method2(self,x,y):
        print("mtd-2 of Sample")
        print("self : \n",self)
        print("x val is : ",x)
        print("y val is : ",y)
        print("=========================")

''' calling '''
s=Sample()
s.method1(10)
s.method2(100,200)

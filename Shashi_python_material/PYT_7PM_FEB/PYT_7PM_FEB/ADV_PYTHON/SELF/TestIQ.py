
class Sample:
    def method1(self):
        print("mtd-1 of Sample")
        print("self :\n",self)
        print("====================")

    def method2(x):
        print("mtd-2 of Sample")
        print("x : \n",x)
        print("=====================")

    def method3(a,b,c):
        print("mtd-3 of Sample")

    def method4(x,self):
        pass

''' calling '''
s=Sample()
s.method1()
s.method2()
s.method3(10,20)
s.method4(100)








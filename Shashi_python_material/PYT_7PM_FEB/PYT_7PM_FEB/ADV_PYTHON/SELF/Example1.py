def myFun():
    print("myFun....")
    
class Sample:
    def method1(self):
        print("mtd-1 of Sample")
        print("self : \n ",self)
        print("===============")

    def method2(self):
        print("mtd-2 of Sample")
        print("self : \n",self)
        print("=================")
        

''' calling '''
myFun( )
s=Sample( )
s.method1( )
s.method2()




import time

class Sample:
    def myData(self,x):
        if isinstance(x,list):
            print("Data is : ",x)
            s=sum(x)
            print("Sum is : ",s)

        elif isinstance(x,tuple):
            print("Data is : ",x)
            m=max(x)
            print("Max is : ",m)

        elif isinstance(x,dict):
            print("Data is : ",x)
            for k,d in x.items():
                time.sleep(.2)
                print(k,d,sep=' <<>>> ')        
        

#calling
s=Sample()

lst=[10,20,30,40,50]
s.myData(lst)

t=(10,20,30,40,50)
s.myData(t)

stu={"sno":101,"sname":"ramesh","scity":"hyd"}
s.myData(stu)

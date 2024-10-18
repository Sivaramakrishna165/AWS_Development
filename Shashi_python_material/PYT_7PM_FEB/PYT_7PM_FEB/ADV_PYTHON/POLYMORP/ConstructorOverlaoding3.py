
import time

class Student:
    def __init__(self,**kwargs):        
        for k,d in kwargs.items():
            time.sleep(.2)
            print(k,d,sep=" >>> ")
        print("=================")
        

''' calling '''
s1=Student(sno=101)
s2=Student(sno=102,sname="ramesh")
s3=Student(sno=103,sname="raj",scity="hyd")

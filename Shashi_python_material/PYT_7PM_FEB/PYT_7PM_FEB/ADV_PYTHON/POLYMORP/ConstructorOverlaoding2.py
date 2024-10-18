


import time
class Sample:    
    def __init__(self,x=None,y=None,z=None):
        time.sleep(1)
        if x!=None and y!=None and z!=None:
            print("const with 3 para Invoked ")
        elif x!=None and y!=None:
            print("const with 2 para Invoked ")
        elif x!=None:
            print("const with 1 para Invoked")
        else:
            print("const without para invoked")

''' calling '''
s1=Sample(10,20,30)
s2=Sample(10,20)
s3=Sample(10)
s4=Sample()

        

import time

'''
r=range(1,10)
for i in r:
    time.sleep(.2)
    print(i)
'''

class MyRange:
    def __init__(self,start,end):
        self.start=start
        self.end=end

    def __iter__(self):
        return self

    def __next__(self):
        self.val=self.start        
        if self.start>self.end:
            raise StopIteration
        
        self.start=self.start+1        
        return self.val            
    

m=MyRange(1,10)
for i in m:
    time.sleep(.2)
    print(i)










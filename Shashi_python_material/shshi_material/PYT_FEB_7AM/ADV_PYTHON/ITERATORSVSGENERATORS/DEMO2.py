''' iterable : str | list | tuple | set | dict
range | filter | map | zip objects
 in these classes PSF overridden
     __iter__(self) and __next__(self)  '''
   

import time

'''
for i in range(1,10,2):
    time.sleep(1)
    print(i)
print("====================")
'''

class myrange:
    def __init__(self,start,end,step=1):
        self.start=start
        self.end=end
        self.step=step

    def __iter__(self):
        return self

    def __next__(self):
        self.val=self.start #1
        self.start=self.start+self.step
        if self.val<=self.end:
            return self.val
        else:
            raise StopIteration()
        

for i in myrange(1,10,2):
    time.sleep(1)
    print(i)
        















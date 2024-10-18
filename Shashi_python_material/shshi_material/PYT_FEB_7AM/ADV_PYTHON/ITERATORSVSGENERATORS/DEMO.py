import time

class Shashi:
    def __init__(self):
        self.courses=["Java",".net","Android"]
        self.index=-1

    def __iter__(self):
        return self

    def __next__(self):
        self.index=self.index+1
        if self.index<len(self.courses):
            return self.courses[self.index]
        else:
            raise StopIteration()

#calling
s=Shashi()
for i in s:
    time.sleep(1)
    print(i)  

''' If u want define u r own class as an  iterable
then we must override __iter__(self) and __next__(self)
from object class.


__iter__(self) should return the object of the class
u want make it as an iterable

whenever we use any iterable object
in the for loop then PVM internally calls
__next__(self) of the class '''














    

import time

lst=[10,20,3.3,"shashi","SssiT"]
for i in lst:
    time.sleep(.2)
    print(i)
print("=========================")



class Shashi:
    def __init__(self):
        self.courses=["Django","MongoDB","Python","Java"]
        self.index=-1

    def __iter__(self):
        return self

    def __next__(self):
        self.index=self.index+1
        if self.index>=len(self.courses):
            raise StopIteration            
        return (self.courses[self.index] )

s=Shashi()
for i in s:
    time.sleep(.2)
    print(i)

''' Note: If any class is overridden
                  __iter__(self) and
                 __next__(self)  Then those classes are
                 Treated by the system as iterables

           __iter__(self) and
           __next__(self) from object class.


           __iter__(self)
               Mtd must return current class object.

          Whenever we use any iterable object in the
          for loop then internally PVM will call
          __next__(self) method of that class.
'''







    

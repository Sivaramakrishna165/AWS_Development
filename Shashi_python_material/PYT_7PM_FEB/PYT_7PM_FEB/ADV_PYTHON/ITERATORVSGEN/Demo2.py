import time

class Shashi:
    def __init__(self):
        self.courses=["Django","Java","C","Python"]
        self.index=-1

    def __iter__(self):
        return self

    def __next__(self):
        self.index=self.index+1
        if self.index>=len(self.courses):
            raise StopIteration
        return self.courses[self.index]

#calling
s=Shashi()
for i in s:
    time.sleep(.2)
    print(i)

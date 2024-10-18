
import threading

class Rat(threading.Thread):
    def run(self):
        for i in range(1,11):
            print("Rat .... ",i)

class Cat(threading.Thread):
    def run(self):
        for i in range(20,31):
            print("Cat >>>> ",i)

#calling
r=Rat()
c=Cat()
r.start()
c.start()

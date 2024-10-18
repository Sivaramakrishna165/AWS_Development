import threading
class Cat:
    def method1(self):
        for i in range(1,11):
            print("cat .... ",i)

class Rat:
    def method2(self):
        for i in range(20,31):
            print("rat >>> ",i)

''' calling '''
c=Cat()
r=Rat()
t1=threading.Thread(target=c.method1)
t2=threading.Thread(target=r.method2)
t1.start()
t2.start()


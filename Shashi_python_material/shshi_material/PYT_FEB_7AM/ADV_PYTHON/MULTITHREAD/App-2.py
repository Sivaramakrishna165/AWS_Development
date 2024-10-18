#App-2
import threading

class Sample:
    def method1(self):
        for i in range(1,11):
            print("mtd-1 ... ",i)

    def method2(self):
        for i in range(20,31):
            print("mtd-2 >>>> ",i)

#calling
s=Sample()
t1=threading.Thread(target=s.method1)
t2=threading.Thread(target=s.method2)
t1.start()
t2.start()

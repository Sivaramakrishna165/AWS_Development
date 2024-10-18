
class Sample:
    @classmethod
    def method1(cls):
        print("cls mtd1")

    def method2(self):
        print("Ins mtd-2")
        self.method1()
        Sample.method1()

#calling
s=Sample()
s.method2()

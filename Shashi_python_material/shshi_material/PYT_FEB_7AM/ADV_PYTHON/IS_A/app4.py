class GFather:
    def House(self):
        print("House From GFather ")

class Father(GFather):
    def Car(self):
        print("Car From Father ")

class Son(Father):
    def Bike(self):
        print("Bike From Son")

    def properties(self):
        self.House()
        self.Car()
        self.Bike()

#calling
s=Son()
s.properties()


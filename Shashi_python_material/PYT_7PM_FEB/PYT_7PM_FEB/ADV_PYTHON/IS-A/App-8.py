
class GFather:
    def House(self):
        print("House From GF")

class Father(GFather):
    def Car(self):
        print("Car From Father ")

class Son(Father):
    def Bike(self):
        print("Bike From Son ")

    def Properties(self):
        self.House()
        self.Car()
        self.Bike()

''' Calling '''
s=Son()
s.Properties()




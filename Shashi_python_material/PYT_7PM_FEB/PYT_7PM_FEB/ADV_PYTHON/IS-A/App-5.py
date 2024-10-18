
class Father:
    def House(self):
        print("House from Father")

class Son(Father):
    def Car(self):
        print("Car From Son ")

''' calling '''
s=Son()
s.House()
s.Car()

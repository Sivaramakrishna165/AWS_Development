
class Father:
    def house(self):
        print("House From Father ")

class Son(Father):
    def car(self):
        print("Car From Son ")

#calling
s=Son()
s.house()
s.car()


class Mother:
    def color(self):
        print("color from mother")

class Father:
    def height(self):
        print("height from father")

class Son(Mother,Father):
    def properties(self):
        print("BTECH From Son ")

#calling
s=Son()
s.color()
s.height()
s.properties()


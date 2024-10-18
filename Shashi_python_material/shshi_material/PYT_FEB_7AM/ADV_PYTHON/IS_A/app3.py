
class Mother:
    def color(self):
        print("color from mother")

class Father:
    def height(self):
        print("height from father")

class Son(Mother,Father):
    def qualifications(self):
        print("BTECH From Son ")
        
    def properties(self):
        self.color()
        self.height()
        self.qualifications()

#calling
s=Son()
s.properties()




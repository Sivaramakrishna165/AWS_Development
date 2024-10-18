
class Father:
    def Height(self):
        print("Height From Father")

class Mother:
    def Color(self):
        print("Color from Mother")

class Son(Father,Mother):
    pass

''' calling '''
s=Son()
s.Height()
s.Color()

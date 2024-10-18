
class Sample:
    def __init__(self):
        print("Const is invoked")

    def __del__(self):
        print("Dest is invoked")

#calling
lst=[Sample(),Sample(),Sample()]
del lst

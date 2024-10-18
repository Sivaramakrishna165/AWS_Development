
class Test:
    def __init__(self):
        print("const is invoked ....")

    def __del__(self):
        print("dest is  invoked .....")

#calling
lst=[Test(),Test(),Test()]
del lst


import pickle
import time

with open("empinfo2.txt","rb") as f:
    while True:
        time.sleep(1)
        try:
            e=pickle.load(f)
        except EOFError:
            break
        else:
            e.getEmployee()


import pickle
import time

f=open("einfo2.txt","rb")

while True:
    time.sleep(1)
    try:
        o=pickle.load(f)
    except EOFError:
        break
    else:
        o.getEmployee()

f.close()

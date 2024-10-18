
import pickle
import mymodule

f=open("einfo2.txt","wb")

while True:
    e=mymodule.Employee()
    pickle.dump(e,f)

    opt=input("do u want another rec y | n ")
    if opt in ['n','N']:
        break        

print("Objects are Saved ")
f.close()

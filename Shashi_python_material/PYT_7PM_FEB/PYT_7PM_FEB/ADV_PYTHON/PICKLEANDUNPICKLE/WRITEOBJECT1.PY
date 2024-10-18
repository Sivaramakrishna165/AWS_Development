
import mymodule
import pickle

e=mymodule.Employee()
f=open("empinfo.txt","wb")
pickle.dump(e,f)
f.close()

print("Object is Saved ")

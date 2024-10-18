
import mymodule
import pickle

f=open("einfo.txt","wb")
e=mymodule.Employee()
pickle.dump(e,f)
print("Object is Saved ")
f.close( )

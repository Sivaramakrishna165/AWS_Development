
import pickle

f=open("einfo.txt","rb")
o=pickle.load(f)
o.getEmployee()
f.close()



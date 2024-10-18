import pickle

with open("empinfo.txt","rb") as f:
    e=pickle.load(f)
    e.getEmployee()

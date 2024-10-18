
import pickle
import mymodule

with open("empinfo2.txt","wb") as f:

    while True:
        e=mymodule.Employee()
        pickle.dump(e,f)
        
        opt=input("do u want another rect y | n ")
        if opt in ['N','n']:
            break


    

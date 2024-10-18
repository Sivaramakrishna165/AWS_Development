import csv,time
fname=input("enter filename ")

try:
    with open(fname,"r") as f:
        ro=csv.reader(f)

        for lst in ro:
            time.sleep(.2)
            for i in lst:
                time.sleep(.2)
                print(i,end='\t')
            print(" ")
            
except FileNotFoundError:
    print("Sorry File Not Found")

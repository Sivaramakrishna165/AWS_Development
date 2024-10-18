



import csv,time

fname=input("Enter CSV File Name : ")
try:
    with open(fname,"r") as f:
        ro=csv.reader(f)

        for row in ro:
            time.sleep(1)
            for i in row:
                time.sleep(.1)
                print(i,end='\t')
            print(" ")

except FileNotFoundError:
    print("Specified File Not Existed ")
    
        

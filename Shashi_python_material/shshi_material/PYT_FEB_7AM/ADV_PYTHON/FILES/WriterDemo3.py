import csv

f=open("stu3.csv","w",newline='')
wo=csv.writer(f)
wo.writerow(["sno","sname","scity"])

while True:
    no=int(input("Enter sno : "))
    name=input("Enter sname : ")
    city=input("Enter city : ")
    wo.writerow([no,name,city])

    opt=input("Do u want another Rec Y | N ")
    if opt in ['N','n']:
        break
    
f.close()
print("Data is Saved ")




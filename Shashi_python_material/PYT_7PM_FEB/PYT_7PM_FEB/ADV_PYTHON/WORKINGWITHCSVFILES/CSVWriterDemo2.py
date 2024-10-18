import csv

f=open("stu3.csv","w",newline='')
wo=csv.writer(f)
wo.writerow(['sno','sname','scity'])

while True:
    sno=input("Enter sno : ")
    sname=input("Enter sname : ")
    scity=input("Enter scity : ")
    wo.writerow([sno,sname,scity])

    opt=input("do u want another y|n : ")
    if opt in ['N','n']:
        break
    
f.close()
print("Data is Saved ")

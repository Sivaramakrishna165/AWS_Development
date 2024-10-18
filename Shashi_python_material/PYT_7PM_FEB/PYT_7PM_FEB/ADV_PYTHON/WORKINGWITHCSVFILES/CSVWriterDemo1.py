import csv

f=open("stu1.csv","w")
wo=csv.writer(f)
lst=['sno','sname','scity']
wo.writerow(lst)
f.close()
print("Data is Saved ")


import csv

f=open("stu.csv","w")
wo=csv.writer(f)
wo.writerow(['sno','sname','scity'])
f.close()
print("Data is Saved ")

import csv,time

with open("stu3.csv","r") as f:
    ro=csv.reader(f)

    for row in ro:
        time.sleep(1)
        print(row[1],"\t",row[2])



        


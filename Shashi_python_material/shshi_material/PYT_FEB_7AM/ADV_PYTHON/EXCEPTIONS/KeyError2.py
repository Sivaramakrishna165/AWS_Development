

stu={"sno":101,"sname":"raj","scity":"hyd"}
print("Student : ",stu)

key=input("Enter key : ")
try:
    name=stu[key]
except KeyError:
    print("Sorry Invalid Key ")
else:
    print("Value is : ",name)

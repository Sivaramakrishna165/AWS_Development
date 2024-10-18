
stu={"sno":101,"sname":"roja","scity":"kadapa"}
print("student : ",stu)
key=input("Enter key : ") #sname
try:
    value=stu[key]
except KeyError:
    print("Sorry Invalid key")
else:
    print("Value is : ",value)

''' Can i write more than one except for a single try ?
    Ans: Yes

    Can i handle more than one exception using
    single except ?
    Ans : Yes

    Can i handle any exception by a single
    Except
    Ans : yes '''
















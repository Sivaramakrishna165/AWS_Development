



#D.update({k:d})
#D.setdefault(k,d=None) -> default value for d is None
#D.fromkeys(iterable,value=None) -> dict

lst=["sai","raj"]
stu={}

d2=stu.fromkeys(lst) #{"sai":None,"raj":None}
print("Result is : ",d2)

d3=stu.fromkeys(lst,"Python") #{"sai":"python","raj":"Python"}
print("Result is : ",d3)
















#D | Dict object reference
#k -> key  | d -> value

''' D.update({k:d})
      * For adding new item to dict
      * For updating an existed item in the dict
      * For concatenation of two dict '''

stu={}

for i in range(1,4):
    k=input("Enter key : ")
    d=input("Enter value : ")
    stu.update({k:d})
    
print("Dict : ",stu)
           




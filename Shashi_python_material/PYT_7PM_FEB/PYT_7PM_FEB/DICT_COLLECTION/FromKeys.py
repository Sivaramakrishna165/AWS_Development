
#D | Dict object reference
#k -> key  | d -> value

''' D.update({k:d})
      * For adding new item to dict
      * For updating an existed item in the dict
      * For concatenation of two dict

   D.setdefault(k[,d])
         default value for d  is None

   D.fromkeys(iterable,value=None) -> dict   
'''

lst=["ravi","nani"]
stu={}

stu1=stu.fromkeys(lst)
print("stu : ",stu1)
print("=================================")

stu2=stu.fromkeys(lst,"Python")
print("stu2 : ",stu2)




















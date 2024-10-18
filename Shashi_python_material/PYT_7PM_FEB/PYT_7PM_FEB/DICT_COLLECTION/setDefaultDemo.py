
#D | Dict object reference
#k -> key  | d -> value

''' D.update({k:d})
      * For adding new item to dict
      * For updating an existed item in the dict
      * For concatenation of two dict

   D.setdefault(k[,d])
         default value for d  is None
'''

stu={"sname":"roja"}
print("stu : ",stu)

stu.setdefault("scity")
stu.setdefault("spin",500090)
stu.setdefault("sname","Sreeja")
print("stu : ",stu)















#D | Dict object reference
#k -> key  | d -> value

''' D.update({k:d})
      * For adding new item to dict
      * For updating an existed item in the dict
      * For concatenation of two dict '''

stu={"sno":101,"sname":"ramesh"}
print("stu : ",stu)
stu.update({"sname":"suresh"})
stu.update({"scity":"hyd"})

print("After update : ",stu)



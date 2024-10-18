
#D | Dict object reference
#k -> key  | d -> value

''' D.update({k:d})
      * For adding new item to dict
      * For updating an existed item in the dict
      * For concatenation of two dict '''

d1={"sno":101,"sname":"roja"}
d2={"scity":"hyd","sname":"srija"}
print("d1 : ",d1)
print("d2 : ",d2)
d1.update(d2)  #d1=d1+d2
print("After Conatenation : ",d1)

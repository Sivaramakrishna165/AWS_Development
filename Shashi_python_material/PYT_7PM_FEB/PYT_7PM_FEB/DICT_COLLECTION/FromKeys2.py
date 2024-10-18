
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

lst_n=["ravi","nani",]
lst_c=["Python","Django","java"]

#zip(iterable,iterable) ->  zip object | iterable
z=zip(lst_n,lst_c)
print("Type is : ",type(z))
print("zip object : ",z)

#dict(iterable)
stu=dict(z)
print("Result is : ",stu)





























lst=["anu","roja","cnu","nani","many"]
print("List : ",lst)
lst2=lst #Ref.copy
print("List : ",lst2)
print("===========================")

#L.copy() -> shallow copy
lst3=lst.copy()
print("List : ",lst3)
print("===========================")

#copy.copy()
import copy
lst4=copy.copy(lst)
print("List : ",lst4)
print("===========================")

#Comprehension
lst5=[i for i in lst]
print("List : ",lst5)












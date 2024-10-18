d={}

''' Adding new item '''
d['sno']=101
d['sname']='Shashi'
print("Data is : ",d)
print("=======================")

''' For updating an item '''
d['sname']='Mr.Kumar'
print("After Update : ",d)
print("=======================")

''' For Reading Value '''
name=d['sname']
print("Value of sname is : ",name)
#d['scity'] KeyError
print("=======================")

''' For Deleting an item '''
del d['sname']
print("After Deleting : ",d)










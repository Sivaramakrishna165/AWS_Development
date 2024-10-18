
sno=101
sname="Ramesh"
age=23 

print("sno is : ",sno)
print("sname is : Mr|Mrs.",sname)
print("sage is : ",age,"yrs")

print("sno is : ",sno,"\n sname is :Mr|Mrs",sname,
      "\n sage is : ",age,"yrs")




'''
output:
    sno is : 101
    sname is : Mr|Mrs.Ramesh
    sage is : 23 yrs

condition : only use format specifiers
    Eg: print("format specifier" %variable)
    print("format specifiers" %(variables) )
'''
print("=========================")
print("sno is : %d" %sno)
print("sname is : Mr|Mrs.%s" %sname)
print("sage is : %d yrs" %age)

print("sno is : %d \n sname is : Mr|Mrs.%s \n sage is :%d yrs"
      %(sno,sname,age),sep='')

















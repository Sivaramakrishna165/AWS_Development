
'''Accept a character from the user
print male if the given char is m or M
print Female if the given char is f or F
else print Third-Gender '''

gender =input("enter any char ")
lstm=['m','M']
lstf=['f','F']

#       0    1    2   3
lst=['m','M','f','F']

#if gender=='m' or gender=='M':
#if gender in lstm:
if gender in lst[0:2:1]:
    print("Male")

#elif gender=='f' or gender=='F':
#elif gender in lstf:
elif gender in lst[2:4:1]:
    print("Female")

else:
    print("Third-Gender")






    

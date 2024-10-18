'''Accept a gender,age from the user
findout the status
     if gender is f | F
        check the age if age>=18 print Major else minor

    if gender is m | M
        check the age if age>=21 print major else minor

    else print third-gender          
'''

gender=input("Enter gender : ")
age=int( input("Enter age : "))
lst=['m','M','f','F']

if gender in lst[0:2:1]:
    if age>=21:
        print("Major")
    else:
        print("Minor")

elif gender in lst[2: : ]:
    print("Major") if age>=18 else print("Minor")

else:
    print("Third-Gender")















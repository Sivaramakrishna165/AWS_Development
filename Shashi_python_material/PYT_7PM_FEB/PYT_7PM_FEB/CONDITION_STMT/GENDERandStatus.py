

''' Accept Gender and age
     findout status of the condidate

   if gender is F | f
      Then check the age if age>=18 then major else minor

    if gender is M | m
      Then check the age if age>=21 then major else minor
'''

gender=input("Enter Gender : ")
age=int(input("Enter age : "))
lstm=['M','m']
lstf=['F','f']
lst=['M','m','F','f']

#if gender=='m' or gender=='M':
#if gender in lstm:
if gender in lst[0:2:1]:
    print("MALE")
    if age>=21:
        print("Major")
    else:
        print("Minor")

#elif gender=='F' or gender=='f':
#elif gender in lstf:
elif gender in lst[2:4:1]:
    print("FEMALE")
    if age>=18:
        print("Major")
    else:
        print("Minor")

else:
    print("Third Gender ")
















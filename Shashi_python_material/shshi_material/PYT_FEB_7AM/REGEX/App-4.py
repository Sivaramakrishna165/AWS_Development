
import re

data=input("Enter mobile number ")
m=re.fullmatch("[6-9][0-9]{9}",data)

if m!=None:
    print("Valid Number")
else:
    print("Sorry Invalid Number ")

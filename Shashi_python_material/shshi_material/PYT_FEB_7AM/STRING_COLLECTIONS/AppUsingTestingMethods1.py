
#input( ) -> str
''' Accept a string from the user
findout No.of.Cap , No.of.Small and
No.of.Digits iff the given string is alnum '''

import time
data=input("Enter u r data : ")

if data.isalnum():
    nc=ns=nd=0    
    for i in data:
        time.sleep(.2)
        if i.isupper():
            nc+=1
        elif i.islower():
            ns+=1
        elif i.isdigit():
            nd+=1

    print("No.of.Cap : ",nc)
    print("No.of.Small : ",ns)
    print("No.of.Digits : ",nd)
else:
    print("Sorry not alnum data ")


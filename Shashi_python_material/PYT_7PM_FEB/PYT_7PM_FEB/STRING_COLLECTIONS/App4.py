''' Accept a string from the user
findout no.of.cap , no.of.small and no.of.
digits in the given string iff string is alphanumerical '''

s=input("Enter u r data : ")
import time

if s.isalnum():
    nc=ns=nd=0
    
    for i in s:
        time.sleep(.5)
        if i.isupper():
            nc+=1
        elif i.islower():
            ns+=1
        elif i.isdigit( ):
            nd+=1

    print("NDdigits : ",nd)
    print("NCap : ",nc)
    print("NSmall : ",ns)
    
        
else:
    print("Sorry Not ALNUM ")


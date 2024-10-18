import time
s=input("Enter u r data ")
nc=ns=nd=nsy=nsp=0

for i in s:
    x=ord(i)
    if x>=65 and x<=90:
        nc+=1
    elif x>=97 and x<=122:
        ns+=1
    elif x>=48 and x<=57:
        nd+=1
    elif x==32:
        nsp+=1
    else:
        nsy+=1

time.sleep(.2)
print("No.of.C : ",nc)
print("No.of.S : ",ns)
print("No.of.D : ",nd)
print("No.of.nsp : ",nsp)
print("No.of.nsy : ",nsy)






import time
s=input("Enter u r data ")
nc=ns=nd=nsy=nsp=0

for i in s:    
    if i>='A' and i<='Z':
        nc+=1
    elif i>='a' and i<='z':
        ns+=1
    elif i>='0' and i<='9':
        nd+=1
    elif i==' ':
        nsp+=1
    else:
        nsy+=1

time.sleep(.2)
print("No.of.C : ",nc)
print("No.of.S : ",ns)
print("No.of.D : ",nd)
print("No.of.nsp : ",nsp)
print("No.of.nsy : ",nsy)






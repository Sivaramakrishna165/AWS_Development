
''' Accept data from the user
findout num of cap | small | digits |
spaces | symb | vowels
in the given string '''

data=input("Enter u r data : ") 
nc=ns=nd=nsy=nsp=nv=0

for i in data:
    x=ord(i)
    if i in "AaEeIiOoUu":
        nv+=1

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

print("No.of.Cap : ",nc)
print("No.of.Small : ",ns)
print("No.of.Dig : ",nd)
print("No.of.Sym : ",nsy)
print("No.of.Space : ",nsp)
print("No.of.Vowel : ",nv)
        
    


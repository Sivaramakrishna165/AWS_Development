
''' Accept data from the user
findout num of cap | small | digits |
spaces | symb | vowels
in the given string '''

data=input("Enter u r data : ") #Welcome
nc=ns=nd=nsy=nsp=nv=0

for i in data:
    if i in ["A","a","E","e","I",'i',"O",'o',"U","u"]:
        nv+=1

    if i.isupper():
        nc+=1
    elif i.islower():
        ns+=1
    elif i.isdigit():
        nd+=1
    elif i.isspace():
        nsp+=1
    else:
        nsy+=1

print("No.of.Cap : ",nc)
print("No.of.Small : ",ns)
print("No.of.Digits : ",nd)
print("No.of.Space : ",nsp)
print("No.of.Sym : ",nsy)
    
   



    
    
    

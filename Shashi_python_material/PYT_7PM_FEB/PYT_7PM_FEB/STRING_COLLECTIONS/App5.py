
s=input("Enter u r data : ")  
nv=nc=nd=nsp=ns=0

for i in s:
    if i in "AaEeIiOoUu":
        nv+=1

    if i.isupper():
        nc+=1
    elif i.islower():
        ns+=1
    elif i.isdigit():
        nd+=1
    elif i.isspace():
        nsp+=1    
   
print("No.of.Vowels : ",nv)
print("No.of.Upper Case : ",nc)
print("No.of.Small : ",ns)
print("No.of.Digits : ",nd)
print("No.of.Spaces : ",nsp)
        



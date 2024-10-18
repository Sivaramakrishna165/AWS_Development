
#write(data)

f=open("data2.txt","w")

data=input("Enter u r data press * for exit ")  #sai

while data!='*':
    f.write(data+"\n")
    data=input( )

f.close()
print("Data is Saved ")

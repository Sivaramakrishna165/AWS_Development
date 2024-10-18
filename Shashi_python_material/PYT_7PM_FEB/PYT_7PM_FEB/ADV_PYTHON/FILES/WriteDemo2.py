


f=open("data2.txt","w")
print("Enter u r data press * For exit ")

data=input() #chinni

while data!='*':
    f.write(data+"\n")
    data=input() 

f.close()
print("Data is Saved")

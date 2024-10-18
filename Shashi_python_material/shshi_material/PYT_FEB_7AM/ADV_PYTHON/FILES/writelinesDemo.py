
#write(data)
#writelines(iterable)

f=open("data3.txt","w")

lst=["1.Have a nice day \n",
         "2.Have a GOOD Day \n",
         "3.Python Training "]

f.writelines(lst)
f.close()
print("Data is Saved ")

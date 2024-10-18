
#writelines(iterable)

f=open("data3.txt","w")

lst=["1.Have a Nice day \n",
        "2.Have a Good Day \n",
        "3.My Dear Friend \n ",
        "4.Happy Learning \n"]

f.writelines(lst)
f.close()
print("Data is Saved ")

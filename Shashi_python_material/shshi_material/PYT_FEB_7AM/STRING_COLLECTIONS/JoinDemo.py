
#S.split([char]) -> list
#S.join(iterable) -> str

lst=['anu','aishu']
s=" and "
s2=s.join(lst) #s2=anu and aishu
print("Result is : ",s2)
print("========================")

s="have a nice day"
lst=s.split( )
print("List : ",lst)
s3=" ".join(lst)
print("Result is : ",s3)

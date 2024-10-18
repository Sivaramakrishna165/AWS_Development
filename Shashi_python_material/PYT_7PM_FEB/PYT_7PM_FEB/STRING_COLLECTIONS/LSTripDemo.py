
#S.lstrip([chars]) -> str
''' it will return new string object
by erasing the specified chars from left side of
the string | by chance if we fail to specify the chars
to trim then it will erase empty space if existed @
left side of the string '''

s1="xysssit"
print("data is : ",s1)
s1=s1.lstrip("xy")
print("Result is : ",s1)
print("===============")

#S.rstrip([chars]) -> str
s3="sssitxy"
print("Data is : ",s3)
s4=s3.rstrip("xy")
print("Result is : ",s4)
print("=================")

#S.strip([chars]) -> str
s5="xysssitxy"
print("Data is : ",s5)
s6=s5.strip("xy")
print("Result is : ",s6)















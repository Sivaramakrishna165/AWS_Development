
#S.split([char]) -> list
#S.join(iterable) -> str

#S.lstrip([chars]) -> str
''' It will return new str object by erasing the specified
chars from the left side of the given string object if we
specify the chars to strip, else it will erase empty spaces
if exists at left side of the string object '''

s1="xysssit"
print("data is : ",s1)
s2=s1.lstrip("xy")
print("Result is : ",s2)
print("=======================")

#S.rstrip([chars]) -> str
s1="sssitxy"
print("data is : ",s1)
s2=s1.rstrip("xy")
print("Result is : ",s2)
print("=========================")

#S.strip([chars]) -> str
s1="xysssitxy"
print("data is : ",s1)
s2=s1.strip("xy")
print("Result is : ",s2)









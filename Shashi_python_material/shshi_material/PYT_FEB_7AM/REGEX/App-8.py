




import re

t=re.subn("d[a-zA-Z]+","####","have a nice day my dear friend")
print("Result is : ",t[0])
print("No.of.Rep : ",t[1])

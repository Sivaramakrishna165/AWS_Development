




import re

#m=re.search("d[a-zA-Z]{2}$","have a nice Day",re.IGNORECASE)
m=re.search("d[a-zA-Z]{2}$","have a nice Day",re.I)
if m!=None:
    print("Target is ends with given pattern")
else:
    print("Target is not ends with given pattern")

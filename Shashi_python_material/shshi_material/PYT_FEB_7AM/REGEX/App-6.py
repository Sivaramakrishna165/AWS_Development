




import re

#m=re.search("d[a-zA-Z]{2}$"," have a nice Day",re.IGNORECASE)

m=re.search("^h[a-zA-Z]{3}","have a nice Day")
if m!=None:
    print("Target is start with given pattern")
else:
    print("Target is not starts with given pattern")

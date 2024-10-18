
import re

p=re.compile("m\w\w")
m=p.match("man mom mad raj ram cnu anu mug")
print("Type is : ",type(m))
print("Match Object : ",m)

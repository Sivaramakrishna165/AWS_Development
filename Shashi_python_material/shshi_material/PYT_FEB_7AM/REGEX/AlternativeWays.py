




import re
#match
p=re.compile("m\w\w")
m=p.match("dad mom mam anu mad sri cnu")
                                          or
m=re.match("m\w\w","dad mom man anu mad sri cnu")

#search
p=re.compile("m\w\w")
m=p.search("dad mom mam anu mad sri cnu")
                                           or
m=re.search("m\w\w","dad mom mam anu mad sri cnu")

#findall
p=re.compile("m\w\w")
lst=p.findall("dad mom mam anu mad sri cnu")
                                           or
lst=re.findall("m\w\w","dad mom mam anu mad sri cnu")


          








#Data from database
DUN="sssit    "
DPW="kphb"

#Data from the user
un=input("Enter Username : ")
'''
un=un.strip()
un=un.lower()
'''
un=un.strip().lower()
pw=input("Enter Password : ")
pw=pw.strip()

#Compare
'''
DUN=DUN.strip()
DUN=DUN.lower()
'''
DUN=DUN.strip().lower()

if un==DUN and pw==DPW:
    print("Valid User ")
else:
    print("Invalid User")


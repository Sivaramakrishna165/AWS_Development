#Data from database
DUN="sssit    "
DPW="kphb"

#Data from the user
un=input("Enter Username : ").strip().lower()
pw=input("Enter Password : ").strip()

#Compare
print("valid user ") if un==DUN.strip().lower() and pw==DPW:
    print("Valid User ")
else:
    print("Invalid User")









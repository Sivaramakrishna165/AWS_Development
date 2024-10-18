#Data from database
DBUN="SSSIT "
DBPW="kphb"

#Data frm user | client
un=input("Enter username : ")
pw=input("Enter password : ")

if un.strip().upper( )==DBUN.strip().upper() and
    pw==DBPW:
    print("Valid User ")
else:
    print("Invalid User ")




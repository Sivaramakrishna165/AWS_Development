
obal=int( input("Enter Oldbal"))
ttype=input("Enter ttype : ")
tamt=int(input("Enter tamt : "))

if ttype in "wW":
    if tamt>obal:
        print("Ins .Funds ")
    elif tamt==obal:
        print("M. M. Bal ")
    else:
        cbal=obal-tamt
        print("Current Bal is : ",cbal)

elif ttype in "dD":
    if tamt>50000:
        print("Req PAN CARD  ")
        opt=input("Do u have PAN Y | N ")

        if opt in "yY":
            cbal=obal+tamt
            print("Current Bal is : ",cbal)
        
    else:
        cbal=obal+tamt
        print("Current Bal is : ",cbal)

else:
    print("Invalid Operation")
    

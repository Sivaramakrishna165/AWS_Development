
oldbal=int(input("Enter Old balance : "))
ttype=input("Enter Ttype : ")
tamt=int(input("Enter Tamount  : "))
lst=['W','w','D','d']

if ttype=='W' or ttype=='w':
    if tamt>oldbal:
        print("INS .Funds")
    elif tamt==oldbal:
        print("M.M.Balance")
    else:
        cbal=oldbal-tamt
        print("Current Bal is : ",cbal)

elif ttype=='d' or ttype=='D':
    if tamt>=50000:
        print("REQ PAN CARD ")
    else:
        cbal=oldbal+tamt
        print("Current Bal is : ",cbal)

else:
    print("Invalid Operation")




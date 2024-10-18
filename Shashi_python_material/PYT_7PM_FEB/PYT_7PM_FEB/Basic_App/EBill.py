''' Accept Present Reading and
previous reading calculate no.of.units
and bill amount '''

prr=int( input("Enter Present Reading ") )
pvr=int( input("Enter Previous Reading ") )

nu=prr-pvr
bill=nu*2

print("===================")
print(" Present Reading : ",prr)
print(" Previous Reading : ",pvr)
print("---------------------------------")
print(" No.of Units : ",nu)
print(" Bill amount : ",bill)
print("=====================")

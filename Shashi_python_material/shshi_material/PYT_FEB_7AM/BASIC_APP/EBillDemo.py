
''' Enter Present Reading , Previous
    Reading calculate nu, bill '''

prr=int( input("Enter Present Reading : "))
pvr=int( input("Enter Previouse Reading : ") )

nu=prr-pvr
bill=nu*2

print("========================")
print(" Present  Reading    : ",prr)
print(" Previous Reading   : ",pvr)
print(" ----------------------------------------")
print(" No.of.units                : ",nu)
print(" Bill amount               : ",bill)
print(" =========================")









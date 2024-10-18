



''' Replacement Fields

        1.Replacement Fields are rep by using { }
        2.While working with replacement fields we
                            must use format( ) from str class.

        3.Replacement Fields can be
                         1.Automatic field number System
                         2.Manual Field Specification.
                                  a.Index Based
                                  b.Name Based

       4. We can't Switch from Automatic <---> Manual

     Syn: print("Replacement Fields".format(variables))
'''

sno=101
sname="Ramesh"
sage=23

print("sno : {} sname is : {} and sage is {}".
      format(sno,sname,sage))

print("sno : {} sname is : {} and sage is {}".
      format(sname,sage,sno))

print("===================================")
print("sno : {2} sname is : {0} and sage is {1}".
      format(sname,sage,sno))

print("===================================")
print("sno : {} sname is : {} and sage is {} {} is Manager".
      format(sno,sname,sage,sname))

print("===================================")
print("sno : {n} sname is : {na} and sage is {a} {na} is Manager".
      format(n=sno,na=sname,a=sage))

print("===================================")
print("sno : {2} sname is : {} and sage is {1} ".
      format(sname,sage,sno))        









#Testing.py
import supermodule

supermodule.specialGreetings()

''' execution of specailGreetings() should be implicit
iff execution process is started from orginal module
[supermodule].

execution of specialGreetings( ) should be explicit
iff the execution process is started outside of the
org module

If u want know from where the execution process is
started from then we have to use predefined
variable of type str is __name__

If the execution is started from org module
then the value of __name__ is '__main__'

if the execution is started from outside of the org
module then the value of __name__ is
modulename which is imported.
'''
















# What is diff between / division vs // [floor division]

''' / division always returns the result in the form
   of float type.

        int / int --> float
        float / int -> float
        int / float -> float
        float / float -> float

  // floor division returns the result based on the
  operand types. and it will return only precision
  value but not scale value.

        int // float --> float
        float // int --> float
        float // float --> float
        int // int --> int
        
'''

print("10/3 ? : ",10/3)
print("10.0/3 ? : ",10.0/3)
print("10/3.0 ? : ",10/3.0)
print("10.0/3.0 ? : ",10.0/3.0)
print("======================")

print("10//3 ? : ",10//3)              
print("10.0//3 ? : ",10.0//3)      
print("10//3.0 ? : ",10//3.0)
print("10.0//3.0 ? : ",10.0//3.0)











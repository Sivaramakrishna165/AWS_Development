
''' what is difference between
      / [division] vs // [floor division]

   division operator always returns the Result in the form
   float type.

         int / int -> float
         float / int -> float
         int / float -> float
         float / float -> float

    // floor division :    12.1212
        * used to return the result based on operand types.
        * It will display only precision value but not scale
                                 value.

            int // int --> int
            print(10//3) #3
            
            float // int -> float
            print(10.0//3) #3.0
            
            int // float -> float
            print(10//3.0)  #3.0
            
            float // float -> float
            print(10.0//3.0) #3.0     

'''

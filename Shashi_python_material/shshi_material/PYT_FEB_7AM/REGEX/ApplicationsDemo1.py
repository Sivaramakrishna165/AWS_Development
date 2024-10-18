




''' Pattern for validating mobile number
    1.total no.of.digits is 10
    2.It must be start with either 6 | 7 |8 | 9 '''

[6-9][0-9][0-9][0-9]
         [0-9][0-9][0-9]
         [0-9][0-9][0-9]

[6-9][0-9]+  //Invalid
[0-9]+ means atleast one time

[6-9][0-9]*  //invalid
[0-9]* means 0 times or any no.of.times

[6-9][0-9]{9}
[0-9]{9} means any digit for 9-times
==================================

''' Pattern for validating mobile number
    1.total no.of.digits is 10 | 11
    2.It must be start with either 6 | 7 |8 | 9
    3.If it is 11 digit then it should starts 0

[6-9][0-9]{9}
0[6-9][0-9]{9}

0?[6-9][0-9]{9}
0? means 0 for 0 time or 1-time

'''


''' Pattern for validating mobile number
    1.total no.of.digits is 10 | 11 | 12
    2.It must be start with either 6 | 7 |8 | 9
    3.If it is 11 digit then it should starts 0
    4.If it is 12 digits then it should starts with 91

91?0?[6-9][0-9]{9}
91? means 91 for 1-time or 0-time
0? means 0 for 1-time or 0-time
9107333333333

(91|0)?[6-9][0-9]{9}
=======================================

Pattern for validating only gmail.com
                  2                            3
|  |---------------------|       |--------------|
s hashikumar.sssit @ gmail.com
[0-9a-zA-Z][a-zA-Z0-9_.]+@gmail[.]com

=======================================
|  |---------------------|       |--------------|
s hashikumar.sssit @ gmail.com
                                        yahoo.com
                                        tv9.con
                                        v6.net




[0-9A-Za-z][a-zA-Z0-9._]+@[a-z0-9]+[.][a-z]+

=======================================
|  |---------------------|       |--------------|
s hashikumar.sssit @ gmail.com
                                         yahoo.com
                                         tv9.con
                                         v6.net

                                         ts.gov.in
                                         uk.edu.online

[a-zA-Z0-9][A-Za-z0-9._]+@[a-z0-9]+ [ [.][a-z]+ ]+
                                         



                                         









                                        





















    






    




















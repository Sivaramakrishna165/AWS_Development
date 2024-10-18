
Userdefined Exception
 1.Defining the User defined Exception
 is nothing but creating a sub class
 of Class Exception

      class Sample:
          pass

      class Sample(ABC): #Abstract class
          pass

        class Sample(Exception): #Exception class
            pass

2. We have to define parameterized constructor
inorder to display exception description along
with Exception name

3.we have to raise the Exception Based on the context
by using raise keyword.







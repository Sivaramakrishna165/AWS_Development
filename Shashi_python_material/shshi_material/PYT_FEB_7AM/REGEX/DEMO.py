
For Regular Expression we have to use
                                               module re

What to Search --> Pattern
                "s"
compile(str) -> pattern class object

Eg: import re
       p=re.compile("s")

Where to Search --> Target   | "shashi"
      match( ) -> Match | None 
      search( ) -> Match | None
      findall( ) -> List   From pattern class
      finditer( ) -> callable_iterator | iterator
             callable_iterator is the collection of Match obj

Match Class Methods
    start( ) -> int
    end( ) -> int 
    group( ) -> str 



      


Working With Files
  - Based on the storage of the data
    programs are classified into 2 types
       1.Non Persistency Prgs.
       2.Persistency Prgs.
              Using Files
              Using Databases

open( ) -> File Class object
   open(filename,filemode)

   File Modes :
        "w" : write mode
             - It will open the file and allow it for writing
             the data into that file.If Specified File is already
             existed then it will overwrite old data with new
                   f=open("Sample","w")

        "a" : append mode
            - It will open the file and allow it for writing
             the data into that file.If Specified File is already
             existed then it will add new data to its previous
                   f=open("sample","a")

          "r": read mode | default mode
                    f=open("sample","r") or
                    f=open("sample")

            - It will open the file and allow it for Reading
            the data from the file.If the specified file is not
            existed then it will raise an Error
                          FileNotFoundError

            "x" : Exclusive Mode
               - It will open the file and allow it for Writing
               the data into that file iff the specified file
               is not existed.By chance if the specified
               File is existed then it will raise Error
                              FileExistsError


        "w+" : write and read
        "a+"  : append and read

      Attributes
        name
        mode
        closed

        Methods
           readable( )
           writable()
           close( )

        For Writing the Data :
              write(data)
              writelines(iterable)

       For Reading
             read( ) -> str
             read(bytes) -> str
             readline( ) -> str
             readlines( ) -> list


      =========================
      os.path.exists(path) -> bool
      os.path.isfile(path) -> bool
      os.path.isdir(path) -> bool







      

             







              




           
        


               
            







                    

             









             

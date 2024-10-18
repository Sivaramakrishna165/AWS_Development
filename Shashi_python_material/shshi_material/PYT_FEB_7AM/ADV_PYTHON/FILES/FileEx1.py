
Working With Files :
    open(str,str) -> File class object
        str - File name
        str - File mode

    File Modes :
        "w" : write mode
             - It will open the File for writing purpose
             - If the specified file is already existed then
               it will overwrite old with new data.
             - If the specified file is not existed then
             it will create new File and allows to write the
             data into it.

         "a" : append mode
             - It will open the File for appending purpose
             - If the specified file is already existed then
               it will add new data to its previous.
             - If the specified file is not existed then
             it will create new File and allows to write the
             data into it.

        "x": Exclusive Mode
            - It will open the file and allows to write the
            data iff the specified file is not existed.
            - If the specified file is existed then it will
            raise an "FileExistsError"

        "r": Read mode
             - It is default mode
             - If the specified File is existed then it will
             open the file and allows us to read the data
             - If the specified file is not existed then
             it will raise "FileNotFoundError"

       "w+" : write and read
        "r+" : read and write






             
             






        









             


             
    

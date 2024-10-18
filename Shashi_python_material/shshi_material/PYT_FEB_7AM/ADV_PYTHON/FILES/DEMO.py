
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

File
   open( ) Function

Properties
   name
   mode
   closed

Methods :
    writable( )
    readable( )
    close( )

 Methods For Writing:
    write(data)
     writelines(iterable)
     
 Methods For Reading :
     read( ) -> str
     read(bytes) -> str
     readline( ) -> tuple
     readlines( ) -> list of tuples

with open( )
tell( )
seek( )

os.path.exists() -> bool
os.path.isfile() -> bool
os.path.isdir() -> bool

exists( )   | isfile( ) | isdir( ) are the functions
from path module existed in the os package

Working with CSV Files:
    - We can store the data using flat files
    - flat files are nothingbut the files which are
    created by using notepad or wordpad
    - in the flat file we can't store the data in the
    form of tables where table support is not existed.

    - Thus here we can store the data in the form
       of tables but each column value is sep by ,
                   CSV
    - File extension should be .csv
    - csv File can be edit in excel

   Steps For Writing Data into CSV File:
       =====================================
       1.open the file in write mode
            f=open("stu.csv","w")
        2.Create CSV writer class object by using
                writer(file)-> writer object
                                from csv module

                   import csv
                   wo=csv.writer(f)

        3.use writerow(iterable) from writer class
                wo.writerow(['sno','sname','scity'])

        4.close the file
                f.close()


    ====================================
    Reading Data From CSV Files :
        1.open the file in read mode
            f=open("stu3.csv","r")

        2.create reader class object by using
            reader(file) -> reader class object
                                   from csv module 

       3.reader class object contains all the records
       existed in the csv File and reader class object
       is iterable
                        

                   




                                











       
    






    
















     




     





   
    




             
             






        









             


             
    

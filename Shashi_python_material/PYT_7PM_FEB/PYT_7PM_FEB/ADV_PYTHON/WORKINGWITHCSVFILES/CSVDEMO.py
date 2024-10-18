
Working With CSV Files
   Flat File are nothing but the
   Files which are defined by using
   notepad or wordpad

   * In The Flat file there is no support for tables
   * In The Flat File we can store the data in the form
   of tables where each column is sep by ,  And
   the File extension should be .csv

   * csv file can be editable in excel applications

   Steps For Writing Data Into CSV Files:
       ================================

   1.open the file in write mode
          f=open("stu1.csv","w") or
          with open("stu1.csv","w") as f

    2.create csvwriter class object using
        writer(file) -> writer class object
                                     from csv module

             import csv
             wo=csv.writer(f)

   3.we have to write the data into csv file by using
              writerow(iterable) from csv writer class
                  wo.writerow(iterable)

   4.close the file





Steps For Reading Data From CSV File:
===================================
1.open the file in read mode
    with open("stu3.csv","r") as f

2.create csv read class object for reading data
from csv Files
            reader(file) -> reader class object  from
            csv module
                import csv
                ro=csv.reader(f)

3.reader class object contains all the records
from csv file.   | read class object is an iterable










        







       
   

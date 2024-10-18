


1.Install Oracle 11.2 and higher version
2.Install cx_Oracle module
        Syn: pip install cx_Oracle     @ command prompt


Steps For Database Prgs:
======================
stp-1 : import cx_Oracle Module,
                    if req any other modules.
                              import cx_Oracle
                              
stp-2 : Est Connection with Oracle Database by using
               following method
                   connect() --> connect class object
                   from cx_Oracle

              connect(str 1 ,str 2 ,str 3)
                 str 3: Database Information
                            Location:portnumber/serviceID
                            localhost:1521

            Every Database Install and Running in fixed
            port number in the System.
            default port number for Oracle Database : 1521

            Every Database is also having unique serviceID
            Default Service ID For Oracle : orcl

            In Oracle
            Syn: SQL>Select * from global_name;
                   -It will return the service id of Oracle DB.
                  
                 str 1: username for the Database
                               eg: scott
                               
                 str 2: password for the database user
                            Eg: tiger

import cx_Oracle

conn=cx_Oracle.connect
("scott","tiger","localhost:1521/orcl5")

Note: If any thing any ways goes wrong then PVM
will raise An Exception " cx_Oracle.DatabaseError '''
    
if conn!=None:
    print("connection is est")
else:
    print("connection is Fail")
=========================================

Stp 3: create cursor object for sending the queries
to the database.
                     By using cursor( ) from conn class it
                     will return cursor class object.

    cur=conn.cursor()
    print("Cursor object is created ")
    
============================================
Stp 4: use the cursor class object for sending the
queries to execute at database, By using following
method
               execute(str) from cursor class.

               str rep: any query i.e Create | Insert |
               update | delete | select command

               cur.execute(command)

Note: After Executing Insert | update | delete
commands the we must call commit( ) from
connection class other wise those changes are not
effected to DB.
                            Eg:  conn.commit( )

Note: if u want we can cancel last transaction by
using rollback( ) from connection class.
                                Eg: conn.rollback( )

=========================================
Step-5: After executing any select statement
Then result of the select statement will be stored
in the same cursor object only.

If u want read the records from the cursor object
     then we have to use the following methods from
             cursor class.

             fetchone( ) -> tuple
             fetchmany( ) -> list of tuples
             fetchall( ) -> list of tuples

Step-6: Process Database result in the PDB Prgs.
Step-7 : close the cursor and connection objects

                    cur.close( )
                    conn.close( )


#In the Oracle
#To Create table to store the data
    Syn: Create table  tablename(
        <columnname>   <datatype>(size),......
        <column n>   <datatype>(size) );

#To Insert a rec into the table
     Syn: Insert <into>  <tablename>
     values(<value1>,<value2>,....,<value n>);


#To Update rec
     Syn: UPDATE <tablename>
     SET  <columnname>=<value>,<column2>=<value>...
     [WHERE <condition>];








                    










             

                            


               








    




    








    

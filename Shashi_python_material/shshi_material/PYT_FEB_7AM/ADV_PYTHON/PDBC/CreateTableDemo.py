
1.Install Python 3.6 and h.version
2.Install Oracle 11.2 h.version
3.Install cx_Oracle module
    a.Open command prompt
    b.Type the following command
          - pip install cx_Oracle

==================================
Steps For PDBC :
    1.import cx_Oracle if req any another modules.
        import cx_Oracle
        import time

    2.Est connection with Oracle Database by using
        connect( ) from cx_Oracle
        connect(str,str,str) -> Connection class object
            str rep : user name of DB | scott
            str rep : password of DB | tiger
            str rep : DB Information
                            location : port number / serviceID

            port number:
                 - Every database is having unique
            port number ,
                 - Port numbers are fixed for every
            database .
                  - fixed port number for Oracle is 1521
                ================================
                Service ID :
                       * Every Database will have service ID
                       * Service ID's of Database are not fixed
                       * Default service id of Oracle "orcl"

          In Oracle:
               SQL>Select * from global_name;
            
            localhost:1521/orcl5
            
App-1:
import cx_Oracle
conn=cx_Oracle.connect
       ("scott","tiger","localhost:1521/orcl5")

if conn!=None:
    print("connection is Est ")
else:
    print("connection is Fail")
===================================

Step-3:
    Create Cursor object For sending Queries to DB
by using cursor( ) from connection class.
               cursor( ) -> cursor class object.
                              Eg:  cur=conn.cursor()

Step-4:
    Use the cursor object for sending queries to
    execute at Database.By using the following mtd
                    execute(str) from cursor class.
                     cur.execute(str)
                         str rep : any query CREATE | INSERT
                         UPDATE | DELETE | SELECT command

    Note : After insert or update or delete command
    we have to call commit( ) from connection class
    otherwise those changes are not effected to DB.

                          conn.commit()

    * IF u want cancel the last transaction then we
    have to call rollback( ) from connection class.
                        conn.rollback( )

    Note:  After executing "Select" statement then
    Result of the select  statement will be stored
    in the same cursor object

        * If u want read the data from cursor object
            then we have to use the following methods
                 fetchone( ) -> tuple
                 fetchmany( ) -> list of tuples
                 fetchall( ) -> list of tuples from cursor class.


    Note: After all DB operations we have to close
    cursor and connection objects
                cur.close( )
                conn.close( )
                




     




                 

                 






    


                        




                           

    








                         
    





    
               
    








    
    
          










                            












        




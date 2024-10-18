Steps For PDBC :
==================
1.import cx_Oracle
    If req any another modules.

2.Est connection with Oracle Database by using 
connect() from cx_Oracle module.
           connect(str,str,str)-> Connection class Object

		   str rep : username of DB | scott
		   str rep : password of DB | tiger 
		   str rep : DB Information
		      DB information
			  location : port number / service ID
			  localhost
			  192.197.0.1


Every Database is having unique port number 
Default port number for ORacle : 1521

Every Database is also having service ID
Default Service id Of Oracle : orcl   | orcl5

In Oracle:
SQL>Select * from global_name;


App-1
import cx_Oracle

conn=cx_Oracle.connect
     ("scott","tiger","localhost:1521/orcl5")

if conn!=None:
    print("connection is Est ")
else:
    print("connection is Failed")
	=============================================

Step-3:
Create cursor object For sending the queries to DATABASE
by using cursor( ) from connection Class
    cursor( ) -> cursor Class Object

           cur=conn.cursor()
		   print("Cursor object is created ....")

Step-4:
Use the cursor Class Object For sending queries to execute
At Database by using 
        execute(str query) From cursor
		                  |- Oracle Queries CREATE | INSERT | UPDATE 
						            DELETE | SELECT ....

            cur.execute(query)

Note: After Executing INSERT | UPDATE | DELETE Commands
Then we have to call commit( ) from connection Class.Otherwise
Those Changes are not effected to the Database.

							  conn.commit( )

Note: After Executing SELECT Statement Then Result of 
The Select Statement will be stored in the SAME CURSOR
Object.

             IF u want Read The Records From the Cursor object
			 Then we have to Use the Following Methods from 
			 Cursor class.
			         fetchone( ) -> tuple
					 fetchmany( ) -> list of tuples
					 fetchall( ) -> list of tuples 

Step 5: Close the Cursor and Connection Objects
   cur.close( )
   conn.close()



			      










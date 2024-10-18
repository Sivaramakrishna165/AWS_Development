
'''UPDATE TABLENAME
set <columnname>=<value>
[where <condition>] '''

import cx_Oracle

cur=conn=None

try:
    conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")
except cx_Oracle.DatabaseError as e :
    print("Sorry unable to continue....")
    print("Reason :",e)
    
else:
    print("Connection is est ")
    cur=conn.cursor()
    print("cursor object is created ")

    query="UPDATE EMP SET SAL=sal+%d WHERE job='%s'"
    inc_sal=int( input("Enter increment salary : "))
    job_title=input("Enter job title : ")
    cur.execute(query %(inc_sal,job_title) )
    print(cur.rowcount," Recs are updated ")
    conn.commit()
    
finally:
    if cur!=None:
        cur.close()

    if conn!=None:
        conn.close()
        

#mydbmodule.py

import cx_Oracle

def delete_rec(no):
    conn=cur=None
    try:
        conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")
        
    except cx_Oracle.DatabaseError as e:
        print("Sorry unable to continue....")
        print("Reason : ",e)

    else:
        print("Connection is Est ")
        cur=conn.cursor()
        print("Cursor object is created ")

        query="DELETE FROM EMP WHERE EMPNO=%d"
        cur.execute(query %no)
        conn.commit();
        print(cur.rowcount," Recs are deleted....")
        
    finally:
        if cur!=None:
            cur.close()
        if conn!=None:
            conn.close()

#calling


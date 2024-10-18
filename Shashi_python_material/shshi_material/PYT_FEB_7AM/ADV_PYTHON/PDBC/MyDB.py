#MyDB.py | modulename
import cx_Oracle

def deleteRec(no):
    conn=None
    cur=None
    try:
        conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")

    except cx_Oracle.DatabaseError as e:
        print("Connection is Fail")
        print("Reason : ",e)
        
    else:
        print("connection is Est ")
        cur=conn.cursor()
        print("Cursor object is created ")

        query="delete from emp WHERE empno=%d"
        cur.execute(query %no)
        print(cur.rowcount," Recs are Deleted.....")
        conn.commit()
    
    finally:
        if cur!=None:
            cur.close()

        if conn!=None:
            conn.close()

#calling
#deleteRec(7698)

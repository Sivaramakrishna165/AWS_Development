
import cx_Oracle

conn=None
cur=None

try:
    conn=cx_Oracle.connect("scott","tiger","localhost:1521/orcl5")

except cx_Oracle.DatabaseError as e:
    print("Sorry unable to continue...")
    print("Reason is : ",e)

else:
    print("Connection is Est ")
    cur=conn.cursor()
    print("Cursor object is created ")

    query="INSERT INTO PYTSTUINFO VALUES(%d,'%s','%s')"

    while True:
        no=int(input("enter sno :")  )
        name=input("enter name : ")
        city=input("enter city : ")    
        cur.execute(query %(no,name,city) )
        conn.commit()
        print("Rec is inserted")
        print("====================")

        opt=input("Do u want another Rec Y | N ")
        if opt in ['N','n']:
            break       

finally:
    if cur!=None:
        cur.close()

    if conn!=None:
        conn.close()
        

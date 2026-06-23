import mysql.connector

def get_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            database='EventManagementt',
            user='root',
            password='Win678@'
        )
        if conn.is_connected():
            return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

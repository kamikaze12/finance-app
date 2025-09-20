import psycopg2

def setup_database():
    # Connection details - dari Supabase Anda
    DB_HOST = "db.kknqpdhkcopfhjqiklne.supabase.co"
    DB_PORT = 5432
    DB_NAME = "postgres"
    DB_USER = "postgres"
    DB_PASSWORD = "N@mikaz312"
    
    print("Setting up database di Supabase...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Connected to database successfully!")
        
        # Create pemasukan table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pemasukan (
                id SERIAL PRIMARY KEY,
                jenis VARCHAR(50) NOT NULL,
                keterangan TEXT,
                jumlah INTEGER NOT NULL,
                tanggal DATE DEFAULT CURRENT_DATE
            )
        """)
        
        # Create pengeluaran table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pengeluaran (
                id SERIAL PRIMARY KEY,
                jenis VARCHAR(50) NOT NULL,
                keterangan TEXT,
                jumlah INTEGER NOT NULL,
                tanggal DATE DEFAULT CURRENT_DATE
            )
        """)
        
        print("Tables created successfully!")
        
        # Test insert data
        cur.execute("INSERT INTO pemasukan (jenis, keterangan, jumlah) VALUES (%s, %s, %s)", 
                   ("Test", "Data test setup", 100000))
        cur.execute("INSERT INTO pengeluaran (jenis, keterangan, jumlah) VALUES (%s, %s, %s)", 
                   ("Test", "Data test setup", 50000))
        
        print("Test data inserted successfully!")
        
        cur.close()
        conn.close()
        
        print("Database setup completed!")
        
    except psycopg2.OperationalError as e:
        print(f"Connection error: {e}")
        print("Please check:")
        print("1. Internet connection")
        print("2. Database credentials")
        print("3. Supabase project status")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    setup_database()
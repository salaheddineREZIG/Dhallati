import os
import sys
from sqlalchemy import text
from app import create_app, db

app = create_app()

with app.app_context():
    try:
        print("🔍 Testing PostgreSQL connection...")
        
        # Test 1: Check PostgreSQL version
        result = db.session.execute(text('SELECT version()'))
        version = result.fetchone()[0]
        print(f"✅ Connected to PostgreSQL!")
        print(f"📊 PostgreSQL version: {version}")
        
        # Test 2: Check current database
        result = db.session.execute(text('SELECT current_database()'))
        db_name = result.fetchone()[0]
        print(f"📁 Current database: {db_name}")
        
        # Test 3: List all tables
        result = db.session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = [row[0] for row in result.fetchall()]
        
        if tables:
            print(f"📊 Tables in database: {', '.join(tables)}")
        else:
            print("📊 No tables found in database (empty)")
            
        # Test 4: Try to create a test table
        try:
            db.session.execute(text('CREATE TABLE IF NOT EXISTS test_connection (id SERIAL PRIMARY KEY, message TEXT)'))
            db.session.commit()
            print("✅ Test table created successfully")
            
            # Insert test data
            db.session.execute(
                text('INSERT INTO test_connection (message) VALUES (:message)'),
                {'message': 'PostgreSQL connection successful!'}
            )
            db.session.commit()
            print("✅ Test data inserted")
            
            # Query test data
            result = db.session.execute(text('SELECT message FROM test_connection'))
            messages = [row[0] for row in result.fetchall()]
            print(f"📝 Test messages: {messages}")
            
            # Clean up
            db.session.execute(text('DROP TABLE test_connection'))
            db.session.commit()
            print("🧹 Test table cleaned up")
            
        except Exception as e:
            print(f"⚠️  Test table operations: {e}")
            db.session.rollback()
            
        print("\n🎉 All tests passed! PostgreSQL is working correctly.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Troubleshooting steps:")
        print("1. Check if PostgreSQL service is running")
        print("2. Verify database credentials in .env file")
        print("3. Check if database 'flaskapp' exists")
        print("4. Verify user 'flaskuser' has proper permissions")
        sys.exit(1)
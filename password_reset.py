"""
Password Reset Script - Set known passwords for testing
"""
import os
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

def reset_passwords():
    """Reset all user passwords to known values"""
    database_url = os.environ.get('DATABASE_URL')
    engine = create_engine(database_url)
    
    # Define password mappings
    password_map = {
        'admin': 'admin',
        'superadmin': 'superadmin', 
        'employee': 'employee'
    }
    
    with engine.connect() as conn:
        for schema in ['development', 'production']:
            print(f"\nResetting passwords in {schema} environment...")
            conn.execute(text(f"SET search_path TO {schema}"))
            
            for username, password in password_map.items():
                # Check if user exists
                user_exists = conn.execute(text("""
                    SELECT COUNT(*) FROM "user" WHERE username = :username
                """), {'username': username}).scalar()
                
                if user_exists:
                    # Update password
                    password_hash = generate_password_hash(password)
                    conn.execute(text("""
                        UPDATE "user" 
                        SET password_hash = :password_hash, verified = true
                        WHERE username = :username
                    """), {'password_hash': password_hash, 'username': username})
                    print(f"Updated {username} password to: {password}")
                else:
                    print(f"User {username} not found in {schema}")
        
        conn.commit()
        print("\nPassword reset completed!")

if __name__ == "__main__":
    reset_passwords()
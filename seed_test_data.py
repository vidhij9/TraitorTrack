"""
Seed the database with test data for development and testing.
This script should be run directly to populate the database with sample parent and child bags.
"""
import requests
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def seed_data():
    """Seed the database with test data by calling the API endpoint"""
    try:
        # Get the base URL from the environment or use default
        base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
        
        # First, we need to login as admin
        login_url = f"{base_url}/login"
        login_data = {
            'username': 'admin',
            'password': 'adminpassword'
        }
        
        # Create a session to maintain cookies
        session = requests.Session()
        
        # Log in as admin
        logger.info("Logging in as admin...")
        login_response = session.post(login_url, data=login_data)
        
        if login_response.status_code != 200:
            logger.error(f"Login failed with status code {login_response.status_code}")
            return False
        
        # Now call the seed_test_data endpoint
        seed_url = f"{base_url}/api/seed_test_data"
        logger.info("Seeding test data...")
        seed_response = session.post(seed_url)
        
        if seed_response.status_code != 200:
            logger.error(f"Seeding failed with status code {seed_response.status_code}")
            logger.error(f"Response: {seed_response.text}")
            return False
        
        # Parse the response
        seed_data = seed_response.json()
        
        if seed_data.get('success'):
            logger.info(f"Success: {seed_data.get('message')}")
            return True
        else:
            logger.error(f"API Error: {seed_data.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"Error seeding data: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting data seeding process...")
    success = seed_data()
    
    if success:
        logger.info("Data seeding completed successfully!")
        sys.exit(0)
    else:
        logger.error("Data seeding failed!")
        sys.exit(1)
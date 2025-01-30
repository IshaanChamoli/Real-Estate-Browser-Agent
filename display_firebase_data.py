import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
from tabulate import tabulate

# Load environment variables
load_dotenv()

def initialize_firebase():
    # Firebase configuration
    config = {
        "apiKey": os.getenv("FIREBASE_API_KEY"),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
        "projectId": os.getenv("FIREBASE_PROJECT_ID"),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
        "appId": os.getenv("FIREBASE_APP_ID"),
        "databaseURL": f"https://{os.getenv('FIREBASE_PROJECT_ID')}-default-rtdb.firebaseio.com"
    }
    
    # Initialize Firebase
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, config)

def get_properties_by_url(url):
    """
    Returns a list of property names that match the given URL.
    
    Args:
        url (str): URL to filter properties by
        
    Returns:
        list: List of property names as strings
    """
    try:
        # Initialize Firebase if not already initialized
        if not firebase_admin._apps:
            initialize_firebase()
        
        # Get reference to the properties node
        ref = db.reference('properties')
        properties = ref.get()
        
        if not properties:
            return []
        
        # Filter properties that match the URL
        matching_properties = []
        search_url = url.strip().lower()
        
        for prop in properties.values():
            property_url = prop.get('url', '').lower()
            if search_url in property_url:
                matching_properties.append(prop.get('name', 'N/A'))
        
        return matching_properties
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

def format_timestamp(timestamp):
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return "N/A"

def display_properties(properties):
    if not properties:
        print("No properties found in the database.")
        return

    # Ask for URL
    search_url = input("Enter URL to filter properties: ").strip().lower()
    
    # Filter properties that match the URL
    matching_properties = []
    for property_id, prop in properties.items():
        property_url = prop.get('url', '').lower()
        if search_url in property_url:
            matching_properties.append(prop.get('name', 'N/A'))

    # Display results
    print("\n=== MATCHING PROPERTIES ===\n")
    
    if not matching_properties:
        print("No properties found matching this URL.")
    else:
        for name in matching_properties:
            print(f"• {name}")
        print(f"\nTotal Matching Properties: {len(matching_properties)}")

def main():
    try:
        initialize_firebase()
        properties = fetch_properties()
        display_properties(properties)
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    url = input("Enter URL to filter properties: ")
    property_names = get_properties_by_url(url)
    print("\nMatching properties:", property_names) 
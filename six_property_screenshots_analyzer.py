import base64
from dotenv import load_dotenv # type: ignore
import os
from typing import List, Dict
from pathlib import Path
import time
import json
import pyrebase # type: ignore
import asyncio
from openai_client import client  # Changed import
from property_screenshotter import create_directory  # Add this import

# Load environment variables from .env file
load_dotenv()

# Initialize Firebase with config from env
firebase_config = {
    "apiKey": os.getenv('FIREBASE_API_KEY'),
    "authDomain": os.getenv('FIREBASE_AUTH_DOMAIN'),
    "databaseURL": f"https://{os.getenv('FIREBASE_PROJECT_ID')}-default-rtdb.firebaseio.com",
    "projectId": os.getenv('FIREBASE_PROJECT_ID'),
    "storageBucket": os.getenv('FIREBASE_STORAGE_BUCKET'),
    "messagingSenderId": os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
    "appId": os.getenv('FIREBASE_APP_ID')
}

# Initialize Firebase
firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

def encode_image(image_path):
    """Function to encode the image to base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_image_paths(folder_path: str) -> List[str]:
    """
    Get paths of all screenshot images in the specified folder,
    sorted by creation timestamp
    
    Args:
        folder_path: Path to folder containing property screenshots
    Returns:
        List of image file paths, sorted by creation time
    """
    image_extensions = ('.png', '.jpg', '.jpeg')
    folder = Path(folder_path)
    
    # Get all image files from folder
    image_files = []
    for ext in image_extensions:
        image_files.extend(folder.glob(f'*{ext}'))
    
    # Sort based on creation timestamp
    def get_creation_time(filepath):
        return os.path.getctime(filepath)
    
    sorted_files = sorted(image_files, key=get_creation_time)
    return [str(f) for f in sorted_files]


def upload_to_firebase(property_data: Dict) -> str:
    """
    Upload property data to Firebase Realtime Database
    
    Args:
        property_data: Dictionary containing property details
    Returns:
        str: ID of the created/updated node
    """
    try:
        # Create a unique node ID based on property name and address
        node_id = f"{property_data['name']}_{property_data['address']}".replace('/', '_').replace(' ', '_')
        
        # Add timestamp
        property_data['timestamp'] = {"timestamp": True}
        
        # Set the data at the specific node
        db.child("properties").child(node_id).set(property_data)
        
        print(f"\n📤 Uploaded to Firebase - Node ID: {node_id}")
        return node_id
        
    except Exception as e:
        print(f"\n❌ Firebase upload error: {str(e)}")
        raise


async def analyze_property_details(property_number: int, property_url: str = None) -> Dict:
    """Analyze screenshots of a specific property listing"""
    print(f"\n🔍 Starting property analysis...")
    print(f"📁 Property number: {property_number}")
    
    # Create directory path using same logic as property_screenshotter
    folder_path = create_directory(property_url, property_number)
    print(f"Looking in directory: {folder_path}")
    
    # Get all image paths from the folder
    image_paths = get_image_paths(folder_path)
    
    if not image_paths:
        raise ValueError(f"No image files found in {folder_path}")
    
    print(f"\n📸 Found {len(image_paths)} screenshots to analyze:")
    for idx, path in enumerate(image_paths, 1):
        creation_time = time.ctime(os.path.getctime(path))
        print(f"  {idx}. {os.path.basename(path)}")
        print(f"     Created: {creation_time}")
        print(f"     Full path: {path}")
    
    print("\n🔄 Preparing images for analysis...")
    
    # Prepare message content
    message_content = [
        {
            "type": "text",
            "text": """Analyze these property listing screenshots and extract the key information.

You MUST respond with a VALID JSON object that has the following format EXACTLY:
{
    "name": "Name of the property/development",
    "address": "Full property address",
    "price": "Listed price (if shown)",
    "url": null,
    "details": "Include ALL other visible information about the property here"
}

IMPORTANT:
1. Your response must start with { and end with }
2. All keys must be in double quotes
3. All values must be in double quotes
4. Do not include any other text, markdown, or code blocks
5. Just return the raw JSON object"""
        }
    ]
    
    # Add each image to the message content
    print("\n🖼️ Converting images to base64...")
    for image_path in image_paths:
        base64_image = encode_image(image_path)
        message_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        })
    print("✅ Images converted successfully")

    print("\n🚀 Sending request to OpenRouter...")
    print("⏳ Waiting for response (this may take a minute)...")
    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": message_content
                }
            ],
            max_tokens=2000
        )
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        print(f"\n✅ Response received! (took {processing_time} seconds)")
        
        print("\n🔍 DEBUG - Raw OpenAI Response:")
        print("="*50)
        print(response.choices[0].message.content)
        print("="*50)
        
        # Get raw response and clean it
        raw_response = response.choices[0].message.content.strip()
        
        # Remove any markdown code block markers
        raw_response = raw_response.replace('```json', '').replace('```', '')
        
        # Clean whitespace
        raw_response = raw_response.strip()
        
        try:
            # Try to parse as is first
            try:
                property_details = json.loads(raw_response)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON
                start_idx = raw_response.find('{')
                end_idx = raw_response.rfind('}') + 1
                if start_idx == -1 or end_idx == 0:
                    raise ValueError(f"No JSON object found in response. Raw response:\n{raw_response}")
                    
                json_str = raw_response[start_idx:end_idx]
                property_details = json.loads(json_str)
            
            print("\n🔄 Successfully parsed JSON:")
            print(json.dumps(property_details, indent=2))
            
            property_details['url'] = property_url
            
            print("\n📤 Uploading to Firebase...")
            doc_id = upload_to_firebase(property_details)
            property_details['firebase_doc_id'] = doc_id
            
            print("\n✅ Analysis complete!")
            print(f"Name: {property_details.get('name', 'Not found')}")
            print(f"Address: {property_details.get('address', 'Not found')}")
            print(f"Price: {property_details.get('price', 'Not found')}")
            
            return property_details
            
        except Exception as e:
            print("\n❌ Error processing response:")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            print("Raw response:", raw_response)
            raise
        
    except Exception as e:
        print(f"\n❌ OpenAI Error: {str(e)}")
        print("Raw response:", response if 'response' in locals() else 'No response received')
        raise


# if __name__ == "__main__":
#     # Example usage when run directly
#     screenshot_folder = "1"
#     property_url = "https://www.strivere.com/listings"
#     try:
#         details = asyncio.run(analyze_property_details(screenshot_folder, property_url))
#         print(json.dumps(details, indent=2))
#     except Exception as e:
#         print(f"\n❌ Error: {str(e)}") 
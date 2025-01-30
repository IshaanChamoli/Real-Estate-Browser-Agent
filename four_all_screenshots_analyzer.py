import base64
from dotenv import load_dotenv # type: ignore
import os
from typing import List
from pathlib import Path
import time
import asyncio

# Load environment variables from .env file
load_dotenv()

# Get OpenAI client from main.py when imported
from openai_client import client


def encode_image(image_path):
    """Function to encode the image to base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_image_paths(folder_path: str) -> List[str]:
    """
    Recursively get paths of all image files in the specified folder and its subdirectories,
    sorted by creation timestamp
    
    Args:
        folder_path: Path to folder containing images
    Returns:
        List of image file paths, sorted by creation time
    """
    image_extensions = ('.png', '.jpg', '.jpeg')
    folder = Path(folder_path)
    
    # Recursively get all image files from folder and subfolders
    image_files = []
    for ext in image_extensions:
        image_files.extend(folder.rglob(f'*{ext}'))
    
    # Sort based on creation timestamp
    def get_creation_time(filepath):
        return os.path.getctime(filepath)
    
    sorted_files = sorted(image_files, key=get_creation_time)
    return [str(f) for f in sorted_files]


async def analyze_real_estate_images(folder_path: str) -> List[str]:
    """Analyze all real estate listing screenshots in a folder"""
    print(f"\n🔍 Analyzing screenshots in folder: {folder_path}")
    
    # Get all image paths from the folder and subfolders
    image_paths = get_image_paths(folder_path)
    
    if not image_paths:
        raise ValueError(f"No image files found in {folder_path} or its subdirectories")
    
    print(f"\n📸 Found {len(image_paths)} screenshots to analyze:")
    
    # Group files by directory for clearer output
    files_by_dir = {}
    for path in image_paths:
        dir_path = os.path.dirname(path)
        if dir_path not in files_by_dir:
            files_by_dir[dir_path] = []
        files_by_dir[dir_path].append(path)
    
    # Print files grouped by directory
    for dir_path, files in files_by_dir.items():
        print(f"\n📁 Directory: {dir_path}")
        for idx, path in enumerate(files, 1):
            creation_time = time.ctime(os.path.getctime(path))
            print(f"  {idx}. {os.path.basename(path)} (Created: {creation_time})")
    
    print("\n🔄 Preparing images for analysis...")
    
    # Updated prompt for specific format
    message_content = [
        {
            "type": "text",
            "text": """Analyze these real estate listing screenshots and list ALL properties in order of appearance. Do NOT list the properties that may signify that they have been sold or are under contract.
            
Format your response EXACTLY like this, with one property per line, starting with a hyphen:
- Property Name 1
- Property Name 2 (123 Main St)
- Property Name 3
- Property Name 2 (456 Oak Ave)

Rules:
1. Start each line with "- "
2. If properties have the same name, add unique identifying info in parentheses
3. No extra text or explanations - just the list
4. No blank lines between properties
5. No numbering, just hyphens"""
        }
    ]
    
    # Add each image to the message content
    for image_path in image_paths:
        base64_image = encode_image(image_path)
        message_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        })

    try:
        print("\n🚀 Sending request to OpenRouter...")
        print("⏳ Waiting for response (this may take a minute)...")
        start_time = time.time()
        
        try:
            # Create completion and get response
            print("\n🔍 DEBUG - Sending this message to OpenAI:")
            print("System message:", "You are a helpful assistant that analyzes real estate listings and returns property names in a simple list format.")
            print("User message content length:", len(str(message_content)))
            print("Number of images:", len([m for m in message_content if m.get('type') == 'image_url']))
            
            # Make request following OpenAI vision format
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # OpenRouter's model name
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analyze these real estate listing screenshots and list ALL properties in order of appearance. Do NOT list the properties that may signify that they have been sold or are under contract.
                                
Format your response EXACTLY like this, with one property per line, starting with a hyphen:
- Property Name 1
- Property Name 2 (123 Main St)
- Property Name 3
- Property Name 2 (456 Oak Ave)

Rules:
1. Start each line with "- "
2. If properties have the same name, add unique identifying info in parentheses
3. No extra text or explanations - just the list
4. No blank lines between properties
5. No numbering, just hyphens"""
                            }
                        ] + [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encode_image(image_path)}"
                                }
                            } for image_path in image_paths
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            print("\n🔍 DEBUG - Raw API Response:")
            print("Response type:", type(response))
            print("Full response:", response)
            print("\nResponse content:")
            try:
                content = response.choices[0].message.content
                print(content)
            except Exception as content_error:
                print(f"Error accessing content: {str(content_error)}")
                print("Response structure:", dir(response))
            
            # Parse response into list
            raw_response = response.choices[0].message.content.strip()
            property_list = [
                line[2:].strip() 
                for line in raw_response.split('\n')
                if line.strip().startswith('-')
            ]
            
            return property_list
            
        except Exception as api_error:
            print("\n❌ OpenAI API Error Details:")
            print(f"Error type: {type(api_error)}")
            print(f"Error message: {str(api_error)}")
            if hasattr(api_error, 'response'):
                print("API Response:", api_error.response)
            raise
            
    except Exception as e:
        print(f"\n❌ Main Error:")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        print("Raw response:", response if 'response' in locals() else 'No response received')
        raise


# Standalone example function - simplified
async def run_example():
    """Run an example analysis on a specific folder"""
    screenshots_folder = "Companies/strivere/"
    
    print("\n=== Running Standalone Example ===")
    print(f"Analyzing folder: {screenshots_folder}")
    
    try:
        properties = await analyze_real_estate_images(screenshots_folder)
        
        if properties and isinstance(properties, list):
            print("\n✅ Success! Found properties:")
            for idx, prop in enumerate(properties, 1):
                print(f"{idx}. {prop}")
            return properties
        else:
            print("\n⚠️ No valid properties found")
            return []
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return []


if __name__ == "__main__":
    # Example usage when run directly
    try:
        print("\n🔄 Starting property analysis example...")
        
        # Create and set event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the example once
        result = loop.run_until_complete(run_example())
        
        # Print final results
        print("\n📊 Final Results:")
        if result:
            print(f"Found {len(result)} properties:")
            for idx, prop in enumerate(result, 1):
                print(f"{idx}. {prop}")
        else:
            print("No properties found or an error occurred")
            
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running example: {str(e)}")
    finally:
        # Ensure the loop is closed
        try:
            loop.close()
        except:
            pass
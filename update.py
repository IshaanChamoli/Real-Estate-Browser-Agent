import asyncio
import os
from dotenv import load_dotenv
from typing import List
from datetime import datetime
import json

# Import required functions
from display_firebase_data import get_properties_by_url
from one_listings_page import listings_page
from two_listings_screenshotter_manual import capture_viewport_screenshots
from three_listings_screenshotter_agent import run_listings_screenshotter
from four_all_screenshots_analyzer import analyze_real_estate_images
from five_property_details_agent import process_property_listing
from six_property_screenshots_analyzer import analyze_property_details
from openai_client import client

async def check_property_updates(company_url: str):
    """
    Compare existing Firebase properties with current website listings
    
    Args:
        company_url: Main website URL of the real estate company
    """
    try:
        print("\n=== Property Listings Update Checker ===")
        
        # Step 1: Get existing properties from Firebase
        print("\n📂 Getting existing properties from Firebase...")
        existing_properties = get_properties_by_url(company_url)
        
        print("\n=== Existing Properties ===")
        if existing_properties:
            for idx, prop in enumerate(existing_properties, 1):
                print(f"{idx}. {prop}")
        else:
            print("No existing properties found in Firebase")
        
        # Step 2: Get current listings URL
        print("\n🔍 Finding current listings page...")
        listings_urls = await listings_page(company_url)
        if not listings_urls:
            raise ValueError("No listings page found!")
        main_listings_url = listings_urls[0]
        print(f"✅ Found listings page: {main_listings_url}")
        
        # Step 3: Take screenshots
        take_screenshots = input("\n❓ Take new screenshots? (yes/no): ").lower().strip()
        if take_screenshots == 'yes':
            print("\n📸 Taking screenshots of current listings...")
            print("3a. Using manual screenshotter...")
            await capture_viewport_screenshots(main_listings_url)
            print("3b. Using agent screenshotter...")
            await run_listings_screenshotter(main_listings_url)
        else:
            print("\n⏩ Using existing screenshots...")
        
        # Step 4: Analyze screenshots to get current property list
        print("\n🔍 Analyzing screenshots for current properties...")
        domain = main_listings_url.split("//")[-1].split("/")[0].replace("www.", "")
        screenshots_folder = f"Companies/{domain.split('.')[0]}"
        current_properties = await analyze_real_estate_images(screenshots_folder)
        
        print("\n=== Current Properties ===")
        if current_properties:
            for idx, prop in enumerate(current_properties, 1):
                print(f"{idx}. {prop}")
        else:
            print("No current properties found")
        
        # Print summary
        print("\n=== Summary ===")
        print(f"Existing properties in Firebase: {len(existing_properties)}")
        print(f"Current properties on website: {len(current_properties)}")
        
        # New code: Compare lists using OpenAI
        print("\n🔍 Analyzing differences using AI...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": f"""Compare these two lists of properties and identify which properties from List 2 are NEW (not present in List 1). Some properties on List 1 might not have the address, and list 2 might, but focus on the main property name! If the name of the property is the same (even if address is only mentioned in one place), do NOT count it as a new property.

List 1 (Firebase properties):
{existing_properties}

List 2 (Current properties):
{current_properties}

IMPORTANT: Return your response in EXACTLY this format, with NO code blocks, NO extra text, just the raw list:
[
    "Property Name 1 (123 Main St)",
    "Property Name 2",
    "Property Name 3 (456 Oak Ave)"
]

Rules:
1. Start with [ and end with ]
2. Each property on a new line
3. Each property in double quotes
4. Include commas between items
5. Include addresses in parentheses if available
6. NO ```python or ``` markers
7. NO other text before or after the list"""
                }
            ],
            max_tokens=1000
        )
        
        # Parse OpenAI's response into a Python list
        try:
            ai_response = response.choices[0].message.content.strip()
            print("\n🤖 AI Analysis Complete!")
            print("\n=== New Properties ===")
            
            # Remove any code block markers if present
            ai_response = ai_response.replace('```python', '').replace('```', '').strip()
            
            # Extract everything between [ and ]
            start_idx = ai_response.find('[')
            end_idx = ai_response.rfind(']') + 1
            if start_idx != -1 and end_idx > 0:
                list_str = ai_response[start_idx:end_idx]
                new_properties = eval(list_str)  # Safe since we're expecting a list
                if new_properties:
                    for idx, prop in enumerate(new_properties, 1):
                        print(f"{idx}. {prop}")
                    print(f"\nFound {len(new_properties)} new properties!")
                    
                    # Process each new property
                    print("\n🏢 Processing new properties...")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    domain = main_listings_url.split("//")[-1].split("/")[0].replace("www.", "")
                    results_dir = f"Results/{domain.split('.')[0]}_{timestamp}"
                    os.makedirs(results_dir, exist_ok=True)
                    
                    firebase_uploads = 0
                    all_properties_data = []
                    
                    for idx, property_name in enumerate(new_properties, 1):
                        print(f"\n=== Processing New Property {idx}/{len(new_properties)} ===")
                        print(f"📍 Property: {property_name}")
                        
                        # Step 1: Get property screenshots using agent
                        print(f"\n1. Getting screenshots for: {property_name}")
                        screenshots_result = await process_property_listing(
                            main_listings_url, 
                            property_name,
                            idx  # Pass the property number
                        )
                        
                        print("\n🔍 DEBUG - Screenshot Result:")
                        print(json.dumps(screenshots_result, indent=2))
                        
                        if screenshots_result.get("status") == "error":
                            print(f"❌ Error taking screenshots: {screenshots_result.get('error', 'Unknown error')}")
                            continue
                        
                        # Step 2: Analyze screenshots and upload to Firebase
                        print(f"\n2. Analyzing screenshots for: {property_name}")
                        print(f"Property number: {idx}")
                        print(f"Property URL: {main_listings_url}")
                        
                        print("\n🔍 MOVING TO PROPERTY SCREENSHOT ANALYZER...")
                        
                        try:
                            # Pass property number and MAIN company URL
                            property_data = await analyze_property_details(
                                property_number=idx,
                                property_url=company_url  # Pass main company URL instead of listings URL
                            )
                            
                            if not property_data:
                                print("❌ No property data returned from analysis")
                                continue
                            
                            # Save results
                            firebase_uploads += 1
                            all_properties_data.append(property_data)
                            
                            property_file = f"{results_dir}/property_{idx}.json"
                            with open(property_file, 'w') as f:
                                json.dump(property_data, f, indent=2)
                            
                            print(f"✅ Property {property_name} complete!")
                            print(f"📄 Data saved to: {property_file}")
                            print(f"📤 Firebase doc ID: {property_data.get('firebase_doc_id')}")
                            
                        except Exception as analysis_error:
                            print(f"❌ Error analyzing property {property_name}:")
                            print(f"Error type: {type(analysis_error)}")
                            print(f"Error message: {str(analysis_error)}")
                            continue
                    
                    # Save final results
                    all_results_file = f"{results_dir}/all_new_properties.json"
                    with open(all_results_file, 'w') as f:
                        json.dump(all_properties_data, f, indent=2)
                    
                    print(f"\n=== Final Update Results ===")
                    print(f"✅ All results saved to: {all_results_file}")
                    print(f"📊 Processed {len(all_properties_data)} of {len(new_properties)} new properties")
                    print(f"📤 Uploaded {firebase_uploads} new properties to Firebase")
                else:
                    print("No new properties found.")
                return new_properties
            else:
                print("❌ Error: Could not find list in response")
                print("Raw response:", ai_response)
                return []
                
        except Exception as parse_error:
            print(f"❌ Error parsing AI response: {str(parse_error)}")
            print("Raw response:", ai_response)
            return []
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return []

async def main():
    # Load environment variables
    load_dotenv()
    
    # Ensure required API keys are set
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Please set your OPENROUTER_API_KEY in the .env file")
        return
    
    print("=== Property Update Checker ===")
    print("Type 'exit' to end the session")
    
    while True:
        # Get company URL input
        company_url = input("\nEnter the real estate company's main website URL (or 'exit' to quit): \n> ")
        
        if company_url.lower() == 'exit':
            break
            
        if company_url.strip():
            await check_property_updates(company_url)

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("Companies", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Run the main function
    asyncio.run(main()) 
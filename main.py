import asyncio
import os
from dotenv import load_dotenv # type: ignore
from typing import List, Dict
import json
from datetime import datetime

# Import functions from other files
from one_listings_page import listings_page
from two_listings_screenshotter_manual import capture_viewport_screenshots
from three_listings_screenshotter_agent import run_listings_screenshotter
from four_all_screenshots_analyzer import analyze_real_estate_images
from five_property_details_agent import process_property_listing
from six_property_screenshots_analyzer import analyze_property_details

# Remove OpenAI client initialization
from openai_client import client  # Add this import if needed

async def process_real_estate_company(company_url: str):
    """
    Process a real estate company's website to extract all property details
    
    Args:
        company_url: Main website URL of the real estate company
    """
    try:
        print("\n=== Starting Real Estate Data Extraction ===")
        
        # STEP 1: Get listings URL
        print("\n🔍 STEP 1: Finding listings page...")
        listings_urls = await listings_page(company_url)
        if not listings_urls:
            raise ValueError("No listings page found!")
        main_listings_url = listings_urls[0]
        print(f"✅ Found listings page: {main_listings_url}")
        
        # STEP 2: Take screenshots of listings page
        take_screenshots = input("\n❓ Take new screenshots? (yes/no): ").lower().strip()
        if take_screenshots == 'yes':
            print("\n📸 STEP 2: Capturing listings page screenshots...")
            print("2a. Using manual screenshotter...")
            manual_screenshots = await capture_viewport_screenshots(main_listings_url)
            print("2b. Using agent screenshotter...")
            await run_listings_screenshotter(main_listings_url)
        else:
            print("\n⏩ Using existing screenshots...")
        
        # STEP 3: Analyze screenshots to get property list
        print("\n🔍 STEP 3: Analyzing screenshots for property list...")
        domain = main_listings_url.split("//")[-1].split("/")[0].replace("www.", "")
        screenshots_folder = f"Companies/{domain.split('.')[0]}"
        property_list = await analyze_real_estate_images(screenshots_folder)
        print(f"✅ Found {len(property_list)} properties")
        
        # STEP 4: Process each property
        print("\n🏢 STEP 4: Processing individual properties...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = f"Results/{domain.split('.')[0]}_{timestamp}"
        os.makedirs(results_dir, exist_ok=True)
        
        all_properties_data = []
        firebase_uploads = 0
        
        for idx, property_name in enumerate(property_list, 1):
            print(f"\n=== Processing Property {idx}/{len(property_list)} ===")
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
            
            # Check if screenshots were successful
            if screenshots_result.get("status") == "error":
                print(f"❌ Error taking screenshots: {screenshots_result.get('error', 'Unknown error')}")
                continue
                
            # Get the directory from the action result
            directory = None
            if isinstance(screenshots_result.get("data"), str):
                # Extract directory from the success message
                if "Screenshots saved to directory:" in screenshots_result["data"]:
                    directory = screenshots_result["data"].split("Screenshots saved to directory:")[1].split("\n")[0].strip()
            else:
                directory = screenshots_result.get("data", {}).get("directory")
                
            if not directory:
                print("❌ No screenshot directory found in result")
                print("Full result:", json.dumps(screenshots_result, indent=2))
                continue
            
            # Step 2: Analyze those screenshots and upload to Firebase
            print(f"\n2. Analyzing screenshots for: {property_name}")
            print(f"Property number: {idx}")
            print(f"Property URL: {main_listings_url}")
            
            print("\n🔍 MOVING TO PROPERTY SCREENSHOT ANALYZER...")
            
            try:
                # Pass property number instead of directory
                property_data = await analyze_property_details(
                    property_number=idx,  # Pass number instead of folder_path
                    property_url=main_listings_url
                )
                
                if not property_data:
                    print("❌ No property data returned from analysis")
                    continue
                
                # Step 3: Save results
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
        all_results_file = f"{results_dir}/all_properties.json"
        with open(all_results_file, 'w') as f:
            json.dump(all_properties_data, f, indent=2)
        
        print(f"\n=== Final Results ===")
        print(f"✅ All results saved to: {all_results_file}")
        print(f"📊 Processed {len(all_properties_data)} of {len(property_list)} properties")
        print(f"📤 Uploaded {firebase_uploads} properties to Firebase")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

async def main():
    # Load environment variables
    load_dotenv()
    
    # Ensure required API keys are set
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Please set your OPENROUTER_API_KEY in the .env file")
        return
    
    print("=== Real Estate Data Extraction Tool ===")
    print("Type 'exit' to end the session")
    
    while True:
        # Get company URL input
        company_url = input("\nEnter the real estate company's main website URL (or 'exit' to quit): \n> ")
        
        if company_url.lower() == 'exit':
            break
            
        if company_url.strip():
            await process_real_estate_company(company_url)

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("Companies", exist_ok=True)
    os.makedirs("Results", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Run the main function
    asyncio.run(main()) 
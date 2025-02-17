import asyncio
from browser_use import Agent, Controller, ActionResult, Browser # type: ignore
from langchain_openai import ChatOpenAI # type: ignore
import os
from dotenv import load_dotenv # type: ignore
from typing import List, Dict
from property_screenshotter import capture_property_screenshots, create_directory # type: ignore

# Create custom controller for our actions
controller = Controller()

@controller.action('Take property screenshots', requires_browser=True)
async def take_screenshots(address: str, browser: Browser) -> ActionResult:
    """Custom action to capture property screenshots"""
    result = await capture_property_screenshots(address=address, browser=browser)
    return ActionResult(
        extracted_content=f"Screenshots saved to directory: {result['directory']}\nIndividual screenshots: {result['screenshot_paths']}"
    )

async def process_property_listing(company_page: str, property_address: str, property_number: int) -> Dict:
    """Process a single property listing - find it and take screenshots."""
    
    print(f"\n=== Processing: {property_address} (#{property_number}) ===")
    print(f"On website: {company_page}")
    
    # Construct the task prompt
    task = (
        f"Go to {company_page} and find the listing for property: {property_address}\n"
        "1. Search or scroll to find this exact property.\n"
        "2. Click to enter the specific property listing page.\n"
        f"3. Once you are on the correct property page, use the 'Take property screenshots' action with the address '{property_number}'.\n"
        "4. After screenshots are complete, look for any PDF/Flyer download buttons and click them."
    )
    
    # Load environment variables
    load_dotenv()
    
    if not os.getenv("OPENROUTER_API_KEY"):
        raise ValueError("Please set your OPENROUTER_API_KEY in the .env file")

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Initialize the LLM
    llm = ChatOpenAI(
        model="openai/gpt-4",
        api_key=os.getenv('OPENROUTER_API_KEY'),
        base_url="https://openrouter.ai/api/v1",
        temperature=0
    )

    # Create the agent with our custom controller
    agent = Agent(
        task=task,
        llm=llm,
        controller=controller,
        use_vision=True,
        save_conversation_path="logs/conversation.json"
    )

    try:
        # Run the agent
        history = await agent.run(max_steps=30)
        
        if history.has_errors():
            print("Errors encountered:", history.errors())
            return {
                "status": "error",
                "errors": history.errors(),
                "address": property_address
            }
        
        # We don't need to parse the agent history - we know where the screenshots will be!
        directory = create_directory(company_page, property_number)
        
        return {
            "status": "success",
            "data": {"directory": directory},
            "address": property_address
        }

    except Exception as e:
        print(f"Error processing {property_address}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "address": property_address
        }

# async def main():
#     """Example usage"""
#     company_page = "https://www.linc.realty/property-search/"
#     property_address = "Plano Professional Office Park"
    
#     try:
#         result = await process_property_listing(company_page, property_address)
#         print("\nProcessing Result:", result)
            
#     except Exception as e:
#         print(f"An error occurred: {str(e)}")

# if __name__ == "__main__":
#     asyncio.run(main()) 
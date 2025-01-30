import asyncio
from browser_use import Agent, Controller, ActionResult, Browser # type: ignore
from langchain_openai import ChatOpenAI # type: ignore
import os
from dotenv import load_dotenv # type: ignore
from urllib.parse import urlparse

def create_directory(url: str) -> str:
    """
    Creates nested directory structure: Companies/domain_name/agent/
    """
    # Parse domain name from URL and remove www if present
    domain = urlparse(url).netloc.replace('www.', '').split('.')[0]
    
    # Create directory structure
    base_dir = os.path.join("Companies", domain, "agent")
    os.makedirs(base_dir, exist_ok=True)
    
    return base_dir

async def run_listings_screenshotter(url: str):
    """
    Run the listings page screenshotter agent
    """
    try:
        # Initialize the LLM
        llm = ChatOpenAI(
            model="openai/gpt-4",
            api_key=os.getenv('OPENROUTER_API_KEY'),
            base_url="https://openrouter.ai/api/v1",
            temperature=0
        )
        
        # Create save directory
        save_dir = create_directory(url)
        
        # Create custom controller with screenshot saving function
        controller = Controller()
        
        @controller.action('Save viewport screenshot', requires_browser=True)
        async def save_viewport_screenshot(screenshot_name: str, browser: Browser):
            page = await browser.get_current_page()
            path = os.path.join(save_dir, f"{screenshot_name}.png")
            await page.screenshot(path=path, full_page=False)
            return ActionResult(extracted_content=f"Screenshot saved to {path}")

        # Create the agent with specific task instructions
        task = f"""
        Visit this real estate listings page: {url}
        
        Follow these steps:
        1. Wait for the page to load completely
        2. Take a screenshot of the current viewport named 'page_1_view_1'
        3. Slowly scroll down the page, taking screenshots every time new listings come into view
        4. There may also be some internal scrolling required! Make sure to go through that and capture all listings within the internal scroll as well.
        5. Name subsequent screenshots incrementally (page_1_view_2, page_1_view_3, etc)
        6. If you find pagination controls, click to the next page and repeat steps 2-5
        7. Continue until you've captured all pages of listings
        
        Important:
        - Do NOT click on individual property listings
        - Only capture the main listings overview
        - Take overlapping screenshots to ensure no listings are missed
        - Wait for new content to load after scrolling or changing pages
        - Your ultimate goal is to capture screenshots of ALL listings on the page, including those that are not immediately visible in the viewport (scrolling, internal scrolling, pagination, etc. required)
        """

        agent = Agent(
            task=task,
            llm=llm,
            controller=controller,
            use_vision=True,
            save_conversation_path=os.path.join("logs", f"{urlparse(url).netloc.replace('www.', '')}_conversation.json")
        )

        # Run the agent
        history = await agent.run()
        
        # Print results
        print("\n=== Task Completed ===")
        print("Screenshots saved in:", save_dir)
        print("Visited URLs:", history.urls())
        
        if history.has_errors():
            print("\nErrors encountered:", history.errors())

    except Exception as e:
        print(f"An error occurred: {str(e)}")

async def main():
    """
    Main function to run the listings screenshotter
    """
    # Load environment variables
    load_dotenv()
    
    # Ensure OPENROUTER_API_KEY is set
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Please set your OPENROUTER_API_KEY in the .env file")
        return

    print("=== Real Estate Listings Screenshotter ===")
    print("Type 'exit' to end the session")
    
    while True:
        # Get URL input
        url = input("\nEnter the real estate listings page URL (or 'exit' to quit): \n> ")
        
        if url.lower() == 'exit':
            break
            
        if url.strip():
            print("\nStarting screenshot capture...")
            await run_listings_screenshotter(url)

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    asyncio.run(main()) 
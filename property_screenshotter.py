from playwright.async_api import async_playwright
import os
from urllib.parse import urlparse
from typing import List
import asyncio

def create_directory(url: str, number: int) -> str:
    """
    Creates nested directory structure: Properties/domain_name/number/
    
    Args:
        url: Website URL to create folder for
        number: Property number to create subfolder for
    Returns:
        Path to the created directory
    """
    # Parse the domain name from the URL and remove www if present
    domain = urlparse(url).netloc.replace('www.', '').split('.')[0]
    
    # Create main Properties directory if it doesn't exist
    if not os.path.exists("Properties"):
        os.makedirs("Properties")
    
    # Create company-specific directory inside Properties
    company_dir = os.path.join("Properties", domain)
    if not os.path.exists(company_dir):
        os.makedirs(company_dir)
    
    # Create numbered directory inside company directory
    number_dir = os.path.join(company_dir, str(number))
    if not os.path.exists(number_dir):
        os.makedirs(number_dir)
    
    return number_dir

async def capture_property_screenshots(address: str, browser) -> dict:
    """
    Captures viewport-by-viewport screenshots of the current page
    
    Args:
        address (str): The address of the property for organizing screenshots
        browser: The browser instance from the agent
        
    Returns:
        dict: Dictionary containing:
            - screenshot_paths: List of paths to individual screenshots
            - directory: Path to the directory containing all screenshots
    """
    screenshot_paths = []
    
    # Get current page from browser
    page = await browser.get_current_page()
    current_url = await page.evaluate('window.location.href')
    
    # Create directory for screenshots
    save_dir = create_directory(current_url, address)
    
    # Initial wait for page load
    await page.wait_for_timeout(7000)  # Wait 7 seconds for initial load
    
    # Get page dimensions
    page_height = await page.evaluate('document.documentElement.scrollHeight')
    viewport_height = page.viewport_size['height']
    
    # Take screenshots viewport by viewport
    current_scroll = 0
    screenshot_count = 0
    scroll_step = int(viewport_height * 0.8)  # 20% overlap
    
    while current_scroll < page_height:
        # Smooth scroll to position
        await page.evaluate('''
            (scrollTo) => {
                window.scrollTo({
                    top: scrollTo,
                    behavior: 'smooth'
                });
            }
        ''', current_scroll)
        
        # Wait for scroll and content to load
        await page.wait_for_timeout(3000)  # Wait 3 seconds after scroll
        
        # Scroll a tiny bit more to trigger any remaining lazy load
        await page.evaluate('window.scrollBy(0, 150)')
        await page.wait_for_timeout(2000)  # Wait 2 seconds after jiggle
        
        # Scroll back to the correct position
        await page.evaluate(f'window.scrollTo(0, {current_scroll})')
        await page.wait_for_timeout(1000)  # Wait 1 second after repositioning
        
        # Take screenshot of current viewport
        screenshot_path = os.path.abspath(f"{save_dir}/screenshot_{screenshot_count}.png")
        await page.screenshot(path=screenshot_path, full_page=False)
        screenshot_paths.append(screenshot_path)
        
        # Update scroll position for next iteration with overlap
        current_scroll += scroll_step
        screenshot_count += 1
        
        # Update page height in case it changed due to dynamic content
        new_height = await page.evaluate('document.documentElement.scrollHeight')
        if new_height > page_height:
            page_height = new_height
    
    # Take one final screenshot at the bottom
    await page.evaluate(f'window.scrollTo(0, {page_height})')
    await page.wait_for_timeout(3000)  # Wait 3 seconds before final screenshot
    screenshot_path = os.path.abspath(f"{save_dir}/screenshot_{screenshot_count}.png")
    await page.screenshot(path=screenshot_path, full_page=False)
    screenshot_paths.append(screenshot_path)
    
    # Scroll back to top smoothly
    await page.evaluate('''
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    ''')
    await page.wait_for_timeout(2000)  # Wait for scroll to complete
    
    return {
        "screenshot_paths": screenshot_paths,
        "directory": os.path.abspath(save_dir)
    }

# Example usage removed since this will be called from the agent 
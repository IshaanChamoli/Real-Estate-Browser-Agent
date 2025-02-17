import requests
import os
from datetime import datetime

def save_webpage():
    # Get URL from user
    url = input("Please enter the webpage URL: ")
    
    try:
        # Send GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Create a filename using the domain name and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain = url.split("//")[-1].split("/")[0]
        filename = f"{domain}_{timestamp}.html"
        
        # Save the content to an HTML file
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(response.text)
            
        print(f"\nWebpage source code has been saved to: {filename}")
        
    except requests.RequestException as e:
        print(f"\nError fetching the webpage: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    save_webpage()
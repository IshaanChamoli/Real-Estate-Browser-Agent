from openai import OpenAI # type: ignore
import os
from dotenv import load_dotenv # type: ignore

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv('OPENROUTER_API_KEY'),
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Real Estate Data Extractor"
    }
) 
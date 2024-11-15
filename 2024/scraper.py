import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re

def scrape_certificate_data(url, output_dir='certificate_data'):
    """
    Scrape certificate data from URL and save to CSV files
    
    Parameters:
    url (str): URL of the certificate page
    output_dir (str): Directory to save CSV files (default: 'certificate_data')
    
    Returns:
    dict: Dictionary containing DataFrame and path to saved CSV file
    """
    try:
        # Extract certificate ID from URL
        certificate_id = url.strip('/').split('/')[-1]
        
        # Send GET request to the URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract basic information
        certificate_data = {
            'Certificate ID': certificate_id,
            'Course Name': soup.find('h1', {'style': 'color: #002347;font-size: 25px;'}).text.strip(),
            'Student Name': soup.find('strong').text.strip(),
            'Completion Date': soup.find_all('strong')[1].text.strip(),
            'Duration': soup.find_all('strong')[2].text.strip(),
            'Verification URL': url
        }
        
        # Create DataFrame
        df = pd.DataFrame([certificate_data])
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save DataFrame to CSV
        csv_path = os.path.join(output_dir, f'certificate_data_{timestamp}.csv')
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        return {
            'data': df,
            'csv_path': csv_path
        }
        
    except requests.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None
    except Exception as e:
        print(f"Error processing the data: {e}")
        return None

# Example usage
url = "https://data.edu.az/az/verified/2103664/"
result = scrape_certificate_data(url)

if result:
    print("\nCertificate Information:")
    print(result['data'])
    print(f"\nSaved to: {result['csv_path']}")
else:
    print("Failed to scrape the certificate data.")
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import time
from tqdm import tqdm  # For progress bar

def scrape_certificate_range(start_id, end_id, base_url="https://data.edu.az/az/verified/", output_dir='certificate_data'):
    """
    Scrape certificate data for a range of IDs and save to CSV
    
    Parameters:
    start_id (int): Starting certificate ID
    end_id (int): Ending certificate ID
    base_url (str): Base URL for certificates
    output_dir (str): Directory to save CSV files
    
    Returns:
    pd.DataFrame: Combined data from all scraped certificates
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize list to store all certificate data
    all_certificates = []
    
    # Headers for requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Create progress bar
    for certificate_id in tqdm(range(start_id, end_id + 1), desc="Scraping Certificates"):
        url = f"{base_url}{certificate_id}/"
        
        try:
            # Send GET request with timeout
            response = requests.get(url, headers=headers, timeout=10)
            
            # Check if page exists (returns 200 status code)
            if response.status_code == 200:
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check if the page contains actual certificate data
                course_name_element = soup.find('h1', {'style': 'color: #002347;font-size: 25px;'})
                if course_name_element:
                    # Extract certificate information
                    certificate_data = {
                        'Certificate ID': certificate_id,
                        'Course Name': course_name_element.text.strip(),
                        'Student Name': soup.find('strong').text.strip(),
                        'Completion Date': soup.find_all('strong')[1].text.strip(),
                        'Duration': soup.find_all('strong')[2].text.strip(),
                        'Verification URL': url,
                        'Status': 'Success'
                    }
                else:
                    # Page exists but no certificate data
                    certificate_data = {
                        'Certificate ID': certificate_id,
                        'Course Name': '',
                        'Student Name': '',
                        'Completion Date': '',
                        'Duration': '',
                        'Verification URL': url,
                        'Status': 'No Certificate Data'
                    }
            else:
                # Page doesn't exist
                certificate_data = {
                    'Certificate ID': certificate_id,
                    'Course Name': '',
                    'Student Name': '',
                    'Completion Date': '',
                    'Duration': '',
                    'Verification URL': url,
                    'Status': f'Failed (Status: {response.status_code})'
                }
                
        except requests.RequestException as e:
            # Handle request errors
            certificate_data = {
                'Certificate ID': certificate_id,
                'Course Name': '',
                'Student Name': '',
                'Completion Date': '',
                'Duration': '',
                'Verification URL': url,
                'Status': f'Error: {str(e)}'
            }
        
        all_certificates.append(certificate_data)
        
        # Add a small delay to avoid overwhelming the server
        time.sleep(0.5)
    
    # Create DataFrame from all collected data
    df = pd.DataFrame(all_certificates)
    
    # Generate timestamp for unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save the DataFrame to CSV
    csv_path = os.path.join(output_dir, f'certificates_{start_id}_to_{end_id}_{timestamp}.csv')
    df.to_csv(csv_path, index=False, encoding='utf-8')
    
    # Print summary
    successful = len(df[df['Status'] == 'Success'])
    print(f"\nTotal certificates processed: {len(df)}")
    print(f"Successful scrapes: {successful}")
    print(f"Failed scrapes: {len(df) - successful}")
    print(f"\nResults saved to: {csv_path}")
    
    return df

if __name__ == "__main__":
    start_id = 2011101
    end_id = 2011594

    print(f"Starting scrape for certificate IDs {start_id} to {end_id}")
    result_df = scrape_certificate_range(start_id, end_id)
    
# 2019 2020 2011101 2011594
# 2021 2103599  2103717 
# 2022 2022001  2022995

import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin

# Base URL
base_url = "https://data.edu.az/en/verified/"

# Initialize list to hold data
data_list = []

# Iterate over the specified range of IDs (202470 to 202475)
for id_num in range(202470, 202476):
    url = f"{base_url}{id_num}/"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract course title
        course_title = soup.find('h1', style="color: #002347;font-size: 25px;")
        course_title = course_title.get_text(strip=True) if course_title else "N/A"

        # Extract participant's name
        completed_by_tag = soup.find('h3', class_="H3_1qzapvr-o_O-weightNormal_s9jwp5-o_O-fontHeadline_1uu0gyz")
        completed_by = completed_by_tag.get_text(strip=True).replace('Completed by', '').strip() if completed_by_tag else "N/A"

        # Extract completion date and duration
        details = completed_by_tag.find_next_siblings('p') if completed_by_tag else []
        completion_date = details[0].get_text(strip=True) if len(details) > 0 else "N/A"
        duration = details[1].get_text(strip=True) if len(details) > 1 else "N/A"

        # Extract shareable link
        shareable_link = soup.find('input', id="copyInput")
        shareable_link = shareable_link['value'] if shareable_link else "N/A"

        # Append data to list
        data_list.append({
            "Course_Title": course_title,
            "Completed_by": completed_by,
            "Completion_Date": completion_date,
            "Duration": duration,
            "Shareable_Link": shareable_link
        })

# Convert list of data to DataFrame
df = pd.DataFrame(data_list)

# Save DataFrame to CSV
df.to_csv('output.csv', index=False)

print("Data saved to output.csv")

import requests
from bs4 import BeautifulSoup
import re
import time
import os
import json
import csv

def get_congressional_district_links():
    # Base URL for Ballotpedia
    base_url = "https://ballotpedia.org"
    
    # URL for the list of congressional districts
    url = "https://ballotpedia.org/List_of_current_members_of_the_U.S._Congress"
    
    # Headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Send GET request to the URL
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links that match the congressional district pattern
        district_links = []
        
        # Look for links containing "Congressional District" in their text
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.text
            
            # Check if the link is for a congressional district
            if "Congressional_District" in href:
                full_url = href
                district_links.append(full_url)
        
        # Remove duplicates while preserving order
        district_links = list(dict.fromkeys(district_links))
        
        return district_links
    
    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return []


def get_2024_result(url="https://ballotpedia.org/Wyoming's_At-Large_Congressional_District"):
    """
    Fetches the Ballotpedia page for Wyoming's At-Large Congressional District and extracts
    the 2024 election results, including both the general and primary (Democratic and Republican)
    contests.
    
    The function returns a dictionary with three keys:
      - "General": results from the general election, including a "Turnout" field.
      - "Democratic": results from the Democratic primary, including a "Turnout" field.
      - "Republican": results from the Republican primary, including a "Turnout" field.
      - "Nonpartisan": results from the nonpartisan primary, including a "Turnout" field.
      
    Each sub-dictionary maps candidate names to their vote counts (as integers), plus a "Turnout" key
    with the total votes cast in that election.
    
    Parameters:
        url (str): The URL of the Ballotpedia page.
    
    Returns:
        dict: A dictionary containing election results by contest, or an empty dictionary if not found.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print("Error fetching the page:", e)
        return {}
    
    soup = BeautifulSoup(response.content, "html.parser")
    results = {}
    
    # Find the 2024 and 2022 h3 elements to limit the search scope
    h3_2024 = soup.find("h3", string=lambda s: s and "2024" in s)
    h3_2022 = soup.find("h3", string=lambda s: s and "2022" in s)
    
    if not h3_2024:
        print("2024 election section not found.")
        return {}
    
    # Create a new soup with only the content between 2024 and 2022 h3 elements
    if h3_2022:
        # Get all elements between 2024 and 2022
        content_between = []
        current = h3_2024.next_sibling
        while current and current != h3_2022:
            content_between.append(current)
            current = current.next_sibling
        
        # Create a new soup with just this content
        content_html = "".join(str(element) for element in content_between)
        content_soup = BeautifulSoup(content_html, "html.parser")
    else:
        # If no 2022 section found, use everything after 2024
        content_soup = BeautifulSoup("".join(str(element) for element in h3_2024.find_all_next()), "html.parser")
    
    # Utility function to check if an election is canceled
    def is_election_canceled(header):
        next_element = header.find_next_sibling()
        return next_element and "canceled" in next_element.get_text().lower()
    
    # Utility function to extract election results from a given section header.
    def extract_results(header, include_party=False):
        # Find the nearest container with the results table.
        container = header.find_next("div", class_="results_table_container")
        if not container:
            print("Results table container not found after header:", header.get_text(strip=True))
            return {}
        table = container.find("table")
        if not table:
            print("Results table not found after header:", header.get_text(strip=True))
            return {}
        contest_results = {}
        total_votes = 0
        for row in table.find_all("tr"):
            # Skip header rows
            if "non_result_row" in row.get("class", []):
                continue
            cols = row.find_all("td")
            # Expect at least 5 columns: check, thumbnail, candidate, percentage, votes.
            if len(cols) < 5:
                continue
            candidate_cell = cols[2]
            candidate_anchor = candidate_cell.find("a")
            if candidate_anchor:
                candidate_name = candidate_anchor.get_text(strip=True)
            else:
                candidate_name = candidate_cell.get_text(strip=True)
            
            # Extract party affiliation if requested
            if include_party:
                # Look for party affiliation in the candidate cell
                party_text = candidate_cell.get_text(strip=True)
                if "(" in party_text and ")" in party_text:
                    # Extract party from parentheses
                    party_start = party_text.find("(") + 1
                    party_end = party_text.find(")")
                    if party_start < party_end:
                        party = party_text[party_start:party_end]
                        # Add party to candidate name
                        candidate_name = f"{candidate_name} ({party})"
            
            votes_text = cols[-1].get_text(strip=True)
            try:
                votes = int(votes_text.replace(",", ""))
                total_votes += votes
            except ValueError:
                votes = votes_text  # Fallback if conversion fails.
            contest_results[candidate_name] = votes
        
        # Add turnout to the results
        contest_results["Turnout"] = total_votes
        return contest_results
    
    # Extract General election results.
    general_header = content_soup.find("h4", string=lambda s: s and "General election" in s)
    if general_header:
        if is_election_canceled(general_header):
            print("General election is canceled.")
        else:
            general_results = extract_results(general_header, include_party=True)
            results["General"] = general_results
    else:
        print("General election header not found.")
    
    # Check for nonpartisan primary first
    nonpartisan_header = content_soup.find("h4", string=lambda s: s and "Nonpartisan primary election" in s)
    if nonpartisan_header:
        if is_election_canceled(nonpartisan_header):
            print("Nonpartisan primary election is canceled.")
        else:
            nonpartisan_results = extract_results(nonpartisan_header)
            results["Nonpartisan"] = nonpartisan_results
            print("Found nonpartisan primary election.")
    
    # Extract Primary election results for Democratic and Republican contests.
    # Only look for these if no nonpartisan primary was found
    if "Nonpartisan" not in results:
        for party in ["Democratic", "Republican"]:
            primary_header = content_soup.find("h4", string=lambda s: s and f"{party} primary election" in s)
            if not primary_header:
                print(f"{party} primary election header not found.")
                continue
            if is_election_canceled(primary_header):
                print(f"{party} primary election is canceled.")
            else:
                party_results = extract_results(primary_header)
                results[party] = party_results
    
    return results

def save_links_to_file(links, filename="congressional_district_links.txt"):
    try:
        with open(filename, 'w') as f:
            for link in links:
                f.write(f"{link}\n")
        print(f"Successfully saved {len(links)} links to {filename}")
    except IOError as e:
        print(f"Error saving to file: {e}")

def extract_district_name(url):
    """Extract the district name from the URL."""
    # Remove the base URL and any trailing slashes
    path = url.replace("https://ballotpedia.org/", "").rstrip("/")
    
    # Handle special cases
    if "At-Large" in path:
        # For at-large districts, extract the state name
        state = path.split("'s_At-Large")[0].replace("_", " ")
        return f"{state} At-Large"
    
    # For numbered districts, extract state and district number
    match = re.search(r"(.+)'s_(\d+)(?:st|nd|rd|th)_Congressional_District", path)
    if match:
        state = match.group(1).replace("_", " ")
        district_num = match.group(2)
        return f"{state} {district_num}"
    
    # Fallback: return the path with underscores replaced by spaces
    return path.replace("_", " ")

def format_results_for_csv(results, include_turnout=True):
    """Format election results as a string for CSV output."""
    if not results:
        return "No results"
    
    formatted = []
    for candidate, votes in results.items():
        if candidate != "Turnout":
            formatted.append(f"{candidate}: {votes}")
    
    return "; ".join(formatted)

def get_turnout(results):
    """Extract turnout from results."""
    if not results or "Turnout" not in results:
        return "No turnout data"
    
    return results["Turnout"]

def calculate_partisan_advantage(results):
    """
    Calculate the partisan advantage in the general election.
    Returns a string like 'R+57' or 'D+42' indicating the percentage advantage.
    """
    if not results or "General" not in results:
        return "No data"
    
    general_results = results["General"]
    if "Turnout" not in general_results:
        return "No turnout data"
    
    turnout = general_results["Turnout"]
    if turnout == 0:
        return "Zero turnout"
    
    # Find Republican and Democratic candidates
    r_votes = 0
    d_votes = 0
    
    for candidate, votes in general_results.items():
        if candidate == "Turnout":
            continue
        
        # Check if candidate is Republican
        if "(R)" in candidate:
            r_votes = votes
        # Check if candidate is Democratic
        elif "(D)" in candidate:
            d_votes = votes
    
    # Calculate the difference as a percentage
    if r_votes == 0 and d_votes == 0:
        return "No R/D candidates"
    
    difference = r_votes - d_votes
    percentage = (difference / turnout) * 100
    
    # Format as R+XX or D+XX
    if percentage > 0:
        return f"R+{percentage:.1f}"
    elif percentage < 0:
        return f"D+{abs(percentage):.1f}"
    else:
        return "Even"

def main():
    # Get all congressional district links
    print("Fetching all congressional district links...")
    district_links = get_congressional_district_links()
    
    if not district_links:
        print("No congressional district links found.")
        return
    
    print(f"Found {len(district_links)} congressional district links.")
    
    # Save links to file
    save_links_to_file(district_links)
    
    # Create CSV file
    csv_filename = "congressional_district_results_2024.csv"
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        # Write header with Partisan Advantage as the 5th column
        csv_writer.writerow([
            "District", 
            "URI", 
            "2024 General Election - Candidates", 
            "2024 General Election - Turnout",
            "Partisan Advantage",
            "2024 Democratic Primary - Candidates", 
            "2024 Democratic Primary - Turnout",
            "2024 Republican Primary - Candidates", 
            "2024 Republican Primary - Turnout",
            "2024 Nonpartisan Primary - Candidates", 
            "2024 Nonpartisan Primary - Turnout",
        ])
        
        # Process each district
        for i, url in enumerate(district_links):
            print(f"\nProcessing district {i+1}/{len(district_links)}: {url}")
            
            # Extract district name from URL
            district_name = extract_district_name(url)
            
            # Get primary results
            results = get_2024_result(url)
            
            # Format results for CSV
            general_results = format_results_for_csv(results.get("General", {}))
            general_turnout = get_turnout(results.get("General", {}))

            # Calculate partisan advantage
            partisan_advantage = calculate_partisan_advantage(results)
            
            democratic_results = format_results_for_csv(results.get("Democratic", {}))
            democratic_turnout = get_turnout(results.get("Democratic", {}))
            
            republican_results = format_results_for_csv(results.get("Republican", {}))
            republican_turnout = get_turnout(results.get("Republican", {}))

            nonpartisan_results = format_results_for_csv(results.get("Nonpartisan", {}))
            nonpartisan_turnout = get_turnout(results.get("Nonpartisan", {}))
            
            # Write to CSV with Partisan Advantage as the 5th column
            csv_writer.writerow([
                district_name, 
                url, 
                general_results, 
                general_turnout,
                partisan_advantage,
                democratic_results, 
                democratic_turnout,
                republican_results, 
                republican_turnout,
                nonpartisan_results, 
                nonpartisan_turnout
            ])
            
            # Print progress
            print(f"Added {district_name} to CSV")
            
    
    print(f"\nProcessed {len(district_links)} districts.")
    print(f"Results saved to {csv_filename}")

if __name__ == "__main__":
    main()
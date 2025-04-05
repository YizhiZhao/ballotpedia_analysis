import requests
from bs4 import BeautifulSoup
import re
import time
import os
import json

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
    general_header = soup.find("h4", string=lambda s: s and "General election" in s)
    if general_header:
        if is_election_canceled(general_header):
            print("General election is canceled.")
        else:
            general_results = extract_results(general_header, include_party=True)
            results["General"] = general_results
    else:
        print("General election header not found.")
    
    # Extract Primary election results for Democratic and Republican contests.
    for party in ["Democratic", "Republican"]:
        primary_header = soup.find("h4", string=lambda s: s and f"{party} primary election" in s)
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
    
    # Process each district
    for i, url in enumerate(district_links):
        print(f"\nProcessing district {i+1}/{len(district_links)}: {url}")
        
        # Extract district name from URL
        district_name = url.split('/')[-1].replace('%27', '_').replace('%', '_')
        
        # Get primary results
        results = get_2024_result(url)
        
        if results:
            # Print results
            print(f"\nResults for {district_name}:")
            for party, candidates in results.items():
                if candidates:
                    print(f"\n{party} Primary:")
                    # Print turnout first
                    if "Turnout" in candidates:
                        print(f"Turnout: {candidates['Turnout']:,} total votes")
                        # Remove turnout from candidates to avoid printing it twice
                        turnout = candidates.pop("Turnout")
                    
                    # Print candidate results
                    for candidate, votes in candidates.items():
                        print(f"{candidate}: {votes:,} votes")
                    
                    # Add turnout back
                    candidates["Turnout"] = turnout
                else:
                    print(f"\n{party} Primary: No results found")
        else:
            print(f"No results found for {district_name}")
        
        # Add a delay to avoid overwhelming the server
        time.sleep(2)
    
    print(f"\nProcessed {len(district_links)} districts.")

if __name__ == "__main__":
    main()
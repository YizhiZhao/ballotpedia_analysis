import csv
import pandas as pd
import re

def extract_numeric_turnout(turnout_str):
    """
    Extract numeric turnout value from a string.
    Returns 0 if no numeric value is found.
    """
    if not turnout_str or turnout_str == "No turnout data":
        return 0
    
    # Try to extract numeric value
    match = re.search(r'(\d+)', turnout_str)
    if match:
        return int(match.group(1))
    return 0

def extract_partisan_advantage(advantage_str):
    """
    Extract partisan advantage value from a string.
    Returns a tuple of (party, value) where party is 'R' or 'D' and value is the percentage.
    Returns (None, 0) if no valid advantage is found.
    """
    if not advantage_str or advantage_str == "No partisan advantage data":
        return (None, 0)
    
    # Try to extract party and value
    match = re.search(r'([RD])\+(\d+)', advantage_str)
    if match:
        party = match.group(1)
        value = int(match.group(2))
        return (party, value)
    return (None, 0)

def analyze_districts():
    """
    Read the congressional district results CSV file and rank districts by primary turnout.
    Filter out districts with R20+ partisan advantage.
    """
    try:
        # Read the CSV file
        df = pd.read_csv('congressional_district_results_2024.csv')
        
        # Create a new column for primary turnout
        # First try Democratic primary turnout, then nonpartisan primary turnout if available
        df['Primary Turnout'] = df.apply(
            lambda row: extract_numeric_turnout(row['2024 Democratic Primary - Turnout']) 
            if row['2024 Democratic Primary - Turnout'] != "No turnout data" 
            else extract_numeric_turnout(row['2024 Nonpartisan Primary - Turnout']), 
            axis=1
        )
        
        # Extract partisan advantage
        df['Partisan Party'] = df.apply(
            lambda row: extract_partisan_advantage(row['Partisan Advantage'])[0], 
            axis=1
        )
        df['Partisan Value'] = df.apply(
            lambda row: extract_partisan_advantage(row['Partisan Advantage'])[1], 
            axis=1
        )
        
        # Filter out districts with zero turnout (no primary data)
        df_filtered = df[df['Primary Turnout'] > 0]
        
        # Filter out districts with R20+ partisan advantage
        df_filtered = df_filtered[
            (df_filtered['Partisan Party'] == 'D') | 
            ((df_filtered['Partisan Party'] == 'R') & (df_filtered['Partisan Value'] < 20))
        ]
        
        # Sort by primary turnout in ascending order
        df_sorted = df_filtered.sort_values('Primary Turnout')
        
        # Add a rank column based on primary turnout
        df_sorted['Rank'] = range(1, len(df_sorted) + 1)
        
        # Create a new column for turnout source (Democratic or Nonpartisan)
        df_sorted['Turnout Source'] = df_sorted.apply(
            lambda row: 'Democratic Primary' 
            if row['2024 Democratic Primary - Turnout'] != "No turnout data" 
            else 'Nonpartisan Primary', 
            axis=1
        )
        
        # Select and reorder columns for display
        result_df = df_sorted[['Rank', 'District', 'Primary Turnout', 'Turnout Source', 'Partisan Advantage', 'URI']]
        
        # Print the results
        print("\nDistricts Ranked by Primary Turnout (Ascending Order):")
        print("=" * 100)
        print(f"{'Rank':<5} {'District':<30} {'Primary Turnout':<15} {'Source':<20} {'Partisan Advantage':<20} {'URI'}")
        print("-" * 100)
        
        for _, row in result_df.iterrows():
            print(f"{row['Rank']:<5} {row['District']:<30} {row['Primary Turnout']:<15} {row['Turnout Source']:<20} {row['Partisan Advantage']:<20} {row['URI']}")
        
        # Save the sorted results to a new CSV file
        output_file = 'districts_ranked_by_primary_turnout.csv'
        result_df.to_csv(output_file, index=False)
        print(f"\nResults saved to {output_file}")
        
        # Print summary statistics
        print("\nSummary Statistics:")
        print(f"Total districts analyzed: {len(df_sorted)}")
        print(f"Districts with no primary data: {len(df) - len(df_filtered)}")
        print(f"Districts with R20+ advantage (filtered out): {len(df[df['Primary Turnout'] > 0]) - len(df_filtered)}")
        print(f"Average primary turnout: {df_sorted['Primary Turnout'].mean():.0f}")
        print(f"Median primary turnout: {df_sorted['Primary Turnout'].median():.0f}")
        print(f"Minimum primary turnout: {df_sorted['Primary Turnout'].min()}")
        print(f"Maximum primary turnout: {df_sorted['Primary Turnout'].max()}")
        
        # Count districts by turnout source
        source_counts = df_sorted['Turnout Source'].value_counts()
        print("\nDistricts by Turnout Source:")
        for source, count in source_counts.items():
            print(f"{source}: {count} districts")
        
        # Count districts by partisan advantage
        partisan_counts = df_sorted['Partisan Party'].value_counts()
        print("\nDistricts by Partisan Advantage:")
        for party, count in partisan_counts.items():
            if party == 'D':
                print(f"Democratic advantage: {count} districts")
            elif party == 'R':
                print(f"Republican advantage (R+0 to R+19): {count} districts")
        
    except FileNotFoundError:
        print("Error: congressional_district_results_2024.csv file not found.")
        print("Please run the scrape_congressional_districts.py script first to generate the data.")
    except Exception as e:
        print(f"Error analyzing districts: {e}")

if __name__ == "__main__":
    analyze_districts() 
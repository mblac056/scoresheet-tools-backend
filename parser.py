# Barbershop scoresheet parser - converts PDF scoresheets to various formats
from tabula import read_pdf
import pandas as pd
import json
import re
import argparse
import csv
 
def clean_column_name(col_name):
    """Remove BOM and clean up column names."""
    # Remove BOM if present
    if col_name.startswith('ï»¿'):
        col_name = col_name[3:]
    return col_name.strip()

def extract_tables(pdf_path, csv_output_path):
     """
     Extract tables from a PDF into a single CSV file.
 
     Args:
         pdf_path (str): Path to the input PDF file.
         csv_output_path (str): Path to save the output CSV file.
     """
     print("Extracting tables from PDF...")
     try:
         # Extract tables from all pages into a list of DataFrames
         tables = read_pdf(pdf_path, pages="all", multiple_tables=True, stream=True, encoding='latin1')
 
         # Combine all DataFrames into a single DataFrame
         combined_table = pd.concat(tables, ignore_index=True)
 
         # Clean column names
         combined_table.columns = [clean_column_name(col) for col in combined_table.columns]
 
         # Print column names for debugging
         print("\nFound columns in PDF:")
         print(combined_table.columns.tolist())
 
         # Save the combined table to a single CSV file with UTF-8 encoding
         combined_table.to_csv(csv_output_path, index=False, encoding='utf-8-sig')
 
         print(f"CSV file saved to {csv_output_path}")
     except Exception as e:
         print(f"Error extracting tables from PDF: {e}")
         raise  # Re-raise the exception to see the full traceback
 

def convert_scoresheet(pdf_path: str, formats: list[str]) -> dict[str, str]:
    base_path = pdf_path.rsplit('.', 1)[0]
    paths = {}

    if "csv" in formats:
        csv_path = f"{base_path}.csv"
        extract_tables(pdf_path, csv_path)
        paths["csv"] = csv_path

    if "json" in formats:
        json_path = f"{base_path}.json"
        if "csv" not in paths:
            csv_path = f"{base_path}.csv"
            extract_tables(pdf_path, csv_path)
        parse_table(csv_path, json_path)
        paths["json"] = json_path

    if "pivot" in formats:
        pivot_path = f"{base_path}_pivot.csv"
        if "json" not in paths:
            json_path = f"{base_path}.json"
            if "csv" not in paths:
                csv_path = f"{base_path}.csv"
                extract_tables(pdf_path, csv_path)
            parse_table(csv_path, json_path)
        create_pivot_format(json_path, pivot_path)
        paths["pivot"] = pivot_path

    return paths

def extract_scores(row):
    # Try different possible column names
    score_columns = {
        'MUS': ['MUS', 'Music', 'Music Score'],
        'PER': ['PER', 'Performance', 'Performance Score'],
        'SNG': ['SNG', 'Singing', 'Singing Score'],
        'Total': ['Total', 'Total Score', 'Final Score']
    }
    
    scores = {}
    for score_type, possible_names in score_columns.items():
        for col_name in possible_names:
            if col_name in row:
                try:
                    scores[score_type] = float(row[col_name])
                    break
                except (ValueError, TypeError):
                    continue
        if score_type not in scores:
            print(f"Warning: Could not find {score_type} score in columns: {row.keys()}")
            scores[score_type] = 0.0
    
    return scores

def parse_table(csv_path, json_path):
    data = []
    current_group = None
    current_round = 'Finals'  # Default to Finals
    
    # Read the CSV file with pandas to handle the BOM
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    # Clean column names
    df.columns = [clean_column_name(col) for col in df.columns]
    
    # Convert DataFrame to list of dictionaries
    rows = df.to_dict('records')
    
    for row in rows:
        # Try to find the group column
        group_col = None
        for possible_name in ['Group', 'Group Name', 'Name', 'Contestant']:
            if possible_name in row:
                group_col = possible_name
                break
        
        if not group_col:
            print("Warning: Could not find group column. Available columns:", row.keys())
            continue
            
        # Check if this row starts a new group
        if row[group_col] and re.match(r'\d+\.', str(row[group_col])):
            if current_group:
                data.append(current_group)
            
            # Extract placement and group name
            group_parts = str(row[group_col]).split('. ', 1)
            placement = int(group_parts[0])
            group_name = group_parts[1].split(' (')[0]  # Remove district info if present
            
            scores = extract_scores(row)
            
            current_group = {
                'placement': placement,
                'group': group_name,
                'combined_total_scores': scores,
                'rounds': {
                    'Finals': {
                        'scores': scores,
                        'songs': []
                    }
                }
            }
        
        # Process songs/rounds information
        song_col = None
        for possible_name in ['Songs', 'Song', 'Title', 'Selection']:
            if possible_name in row:
                song_col = possible_name
                break
        
        if song_col and row[song_col]:
            if str(row[song_col]).startswith('Total: '):
                continue  # Skip total points rows
            
            # Handle round markers
            for round_name in ['Finals', 'Semi-Finals', 'Quarter-Finals']:
                if str(row[song_col]).startswith(f'{round_name}: '):
                    current_round = round_name
                    if round_name not in current_group['rounds']:
                        current_group['rounds'][round_name] = {'songs': [], 'scores': {}}
                    current_group['rounds'][round_name]['scores'] = extract_scores(row)
                    break
            else:  # This is a song (no round marker matched)
                song_info = {
                    'title': row[song_col],
                    'scores': extract_scores(row)
                }
                current_group['rounds'][current_round]['songs'].append(song_info)

    # Add the last group
    if current_group:
        data.append(current_group)

    # Write to JSON file
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"JSON file saved to {json_path}")

def create_pivot_format(json_path, pivot_csv_path):
     """
     Transform the JSON data into a format suitable for pivot tables.
     
     Args:
         json_path (str): Path to the input JSON file
         pivot_csv_path (str): Path to save the pivot-formatted CSV
     """
     with open(json_path, 'r') as f:
         data = json.load(f)
     
     # Create list to hold all rows
     rows = []
     
     for group_data in data:
         group_name = group_data['group']
         
         # Process each round
         for round_name, round_data in group_data['rounds'].items():
             # Add round total scores
             for category, score in round_data['scores'].items():
                 rows.append({
                     'Group': group_name,
                     'Round': round_name,
                     'Song': 'Round Total',
                     'Category': category,
                     'Score': score
                 })
             
             # Add individual song scores
             for song in round_data['songs']:
                 for category, score in song['scores'].items():
                     rows.append({
                         'Group': group_name,
                         'Round': round_name,
                         'Song': song['title'],
                         'Category': category,
                         'Score': score
                     })
     
     # Convert to DataFrame and save as CSV
     df = pd.DataFrame(rows)
     df.to_csv(pivot_csv_path, index=False, encoding='utf-8')
     print(f"Pivot table format saved to {pivot_csv_path}")
 
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse a barbershop scoresheet PDF into various formats.")
    parser.add_argument("--input", "-i", required=True, help="Path to the input PDF file.")
    parser.add_argument("--formats", "-f", nargs="+", choices=["csv", "json", "pivot"], default=["csv", "json", "pivot"],
                        help="Output formats to generate (default: all)")

    args = parser.parse_args()
    convert_scoresheet(args.input, args.formats)


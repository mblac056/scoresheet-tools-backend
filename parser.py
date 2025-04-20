# Barbershop scoresheet parser - converts PDF scoresheets to various formats
from tabula import read_pdf
import pandas as pd
import json
import re
import argparse
import csv
 
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
         tables = read_pdf(pdf_path, pages="all", multiple_tables=True, stream=True)
 
         # Combine all DataFrames into a single DataFrame
         combined_table = pd.concat(tables, ignore_index=True)
 
         # Save the combined table to a single CSV file with UTF-8 encoding
         combined_table.to_csv(csv_output_path, index=False, encoding='utf-8')
 
         print(f"CSV file saved to {csv_output_path}")
     except Exception as e:
         print(f"Error extracting tables from PDF: {e}")
 

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
     return {
         'MUS': float(row['MUS']),
         'PER': float(row['PER']),
         'SNG': float(row['SNG']),
         'Total': float(row['Total'])
     }
 
 
def parse_table(csv_path, json_path):
     data = []
     current_group = None
     current_round = 'Finals'  # Default to Finals
     
     with open(csv_path, 'r') as f:
         reader = csv.DictReader(f)
         for row in reader:
             # Check if this row starts a new group (has a number followed by period)
             if row['Group'] and re.match(r'\d+\.', row['Group']):
                 if current_group:
                     data.append(current_group)
                 
                 # Extract placement and group name
                 group_parts = row['Group'].split('. ', 1)
                 placement = int(group_parts[0])
                 group_name = group_parts[1].split(' (')[0]  # Remove district info if present
                 
                 current_group = {
                     'placement': placement,
                     'group': group_name,
                     'combined_total_scores': {
                         'MUS': float(row['MUS']),
                         'PER': float(row['PER']),
                         'SNG': float(row['SNG']),
                         'Total': float(row['Total'])
                     },
                     'rounds': {
                         'Finals': {
                             'scores': {
                                 'MUS': float(row['MUS']),
                                 'PER': float(row['PER']),
                                 'SNG': float(row['SNG']),
                                 'Total': float(row['Total'])
                             },
                             'songs': []
                         }
                     }
                 }
             
             # Process songs/rounds information
             if row['Songs']:
                 if row['Songs'].startswith('Total: '):
                     continue  # Skip total points rows
                 
                 # Handle round markers
                 for round_name in ['Finals', 'Semi-Finals', 'Quarter-Finals']:
                     if row['Songs'].startswith(f'{round_name}: '):
                         current_round = round_name
                         if round_name not in current_group['rounds']:
                             current_group['rounds'][round_name] = {'songs': [], 'scores': {}}
                         current_group['rounds'][round_name]['scores'] = extract_scores(row)
                         break
                 else:  # This is a song (no round marker matched)
                     song_info = {
                         'title': row['Songs'],
                         'scores': extract_scores(row)
                     }
                     current_group['rounds'][current_round]['songs'].append(song_info)
 
     # Add the last group
     if current_group:
         data.append(current_group)
 
     # Write to JSON file
     with open(json_path, 'w') as f:
         json.dump(data, f, indent=4)
 
 
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


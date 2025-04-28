# Barbershop scoresheet parser - converts PDF scoresheets to various formats
from tabula import read_pdf
import pandas as pd
import json
import re
import argparse
import PyPDF2  

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

def extract_metadata(pdf_path, txt_output_path):
    """
    Extract metadata from a PDF using PyPDF2 and save to a text file in YAML format.
    
    Args:
        pdf_path (str): Path to the input PDF file.
        txt_output_path (str): Path to save the metadata text file.
        
    Returns:
        dict: Dictionary containing extracted metadata.
    """
    print("Extracting metadata from PDF...")
    metadata = {
        'round_name': '',
        'location': '',
        'date': '',
        'official_panel': {
            'PC': '',
            'ADM': '',
            'MUS': '',
            'PER': '',
            'SNG': ''
        },
        'awards': [],
        'draw': [],
        'mic_tester': '',
        'evaluation_only': [],
        'published': {
            'name': '',
            'date': ''
        },
        'footnotes': [],
        'disqualifications': []
    }
    
    try:
        # Open the PDF file
        with open(pdf_path, 'rb') as file:
            # Create a PDF reader object
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extract text from all pages
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
            
            # Look for "Official Scoring Summary"
            summary_match = re.search(r'Official Scoring Summary\s*(.*?)(?:\n|$)', full_text)
            if summary_match:
                metadata['round_name'] = summary_match.group(1).strip()
            
            # Look for location and date
            location_date_match = re.search(r'(.*?);\s*(.*?)(?:\n|$)', full_text)
            if location_date_match:
                metadata['location'] = location_date_match.group(1).strip()
                metadata['date'] = location_date_match.group(2).strip()
            
            # Look for "Official Panel" - improved extraction
            panel_section = re.search(r'Official Panel\s*(.*?)(?=Awards|Footnotes|Draw|$)', full_text, re.DOTALL)
            if panel_section:
                panel_text = panel_section.group(1).strip()
                
                # Extract panelists by category
                pc_match = re.search(r'PC:\s*(.*?)(?=\n|$)', panel_text)
                if pc_match:
                    metadata['official_panel']['PC'] = pc_match.group(1).strip()
                
                adm_match = re.search(r'ADM:\s*(.*?)(?=\n|$)', panel_text)
                if adm_match:
                    metadata['official_panel']['ADM'] = adm_match.group(1).strip()
                
                mus_match = re.search(r'MUS:\s*(.*?)(?=\n|$)', panel_text)
                if mus_match:
                    metadata['official_panel']['MUS'] = mus_match.group(1).strip()
                
                per_match = re.search(r'PER:\s*(.*?)(?=\n|$)', panel_text)
                if per_match:
                    metadata['official_panel']['PER'] = per_match.group(1).strip()
                
                sng_match = re.search(r'SNG:\s*(.*?)(?=\n|$)', panel_text)
                if sng_match:
                    metadata['official_panel']['SNG'] = sng_match.group(1).strip()
            
            # Look for "Awards" - improved extraction
            awards_section = re.search(r'Awards\s*(.*?)(?=Footnotes|Draw|Evaluation Only|$)', full_text, re.DOTALL)
            if awards_section:
                awards_text = awards_section.group(1).strip()
                
                # Process awards
                award_blocks = re.split(r'\n(?=\d+\s+.*:)', awards_text)
                for block in award_blocks:
                    if not block.strip():
                        continue
                    
                    # Extract award title and winner
                    lines = block.strip().split('\n')
                    award_title = lines[0].strip()
                    winner = ''
                    
                    # Look for winner in subsequent lines
                    for i in range(1, len(lines)):
                        line = lines[i].strip()
                        if line and not line.startswith('Published by'):
                            winner = line
                            break
                    
                    metadata['awards'].append({
                        'award': award_title,
                        'winner': winner
                    })
            
            # Look for "Footnotes" - improved extraction
            footnotes_section = re.search(r'Footnotes\s*(.*?)(?=Draw|Evaluation Only|$)', full_text, re.DOTALL)
            if footnotes_section:
                footnotes_text = footnotes_section.group(1).strip()
                
                # Process footnotes
                for line in footnotes_text.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('Published by'):
                        metadata['footnotes'].append(line)
            
            # Look for "Draw" - improved extraction with mic tester handling
            draw_section = re.search(r'Draw\s*(.*?)(?=Evaluation Only|MT:|Published by|$)', full_text, re.DOTALL)
            if draw_section:
                draw_text = draw_section.group(1).strip()
                
                # Process draw information
                draw_entries = re.findall(r'(\d+):\s*(.*?)(?=\n\d+:|$)', draw_text, re.DOTALL)
                for number, group in draw_entries:
                    metadata['draw'].append({
                        'number': number.strip(),
                        'group': group.strip()
                    })
            
            # Look for mic tester (MT)
            mt_section = re.search(r'MT:\s*(.*?)(?=\n\n|Published by|$)', full_text, re.DOTALL)
            if mt_section:
                mt_text = mt_section.group(1).strip()
                metadata['mic_tester'] = mt_text
            
            # Look for "The following groups performed for evaluation score only" - improved extraction
            eval_section = re.search(r'The following groups performed for evaluation score only:\s*(.*?)(?=\n\n|Published by|Awards|Draw|Footnotes|$)', full_text, re.DOTALL)
            if eval_section:
                eval_text = eval_section.group(1).strip()
                
                # Split by commas and clean up
                eval_groups = [g.strip() for g in eval_text.split(',') if g.strip()]
                metadata['evaluation_only'] = eval_groups
            
            # Look for "Published by" - improved extraction
            published_match = re.search(r'Published by (.*?) at (.*?)(?=\n|$)', full_text)
            if published_match:
                metadata['published']['name'] = published_match.group(1).strip()
                metadata['published']['date'] = published_match.group(2).strip()
            
            # Look for disqualifications - improved extraction
            disqualifications_match = re.search(r'disqualified for violation of the BHS Contest Rules:\s*(.*?)(?=\n\n|$)', full_text, re.DOTALL)
            if disqualifications_match:
                disqualifications_text = disqualifications_match.group(1).strip()
                
                # Split by commas and clean up
                disqualifications = [d.strip() for d in disqualifications_text.split(',') if d.strip()]
                metadata['disqualifications'] = disqualifications
        
        # Save metadata to YAML file
        with open(txt_output_path, 'w', encoding='utf-8') as f:
            f.write("Round Name: " + metadata['round_name'] + "\n")
            f.write("Location: " + metadata['location'] + "\n")
            f.write("Date: " + metadata['date'] + "\n\n")
            
            f.write("Panel:\n")
            f.write("  PC: " + metadata['official_panel']['PC'] + "\n")
            f.write("  ADM: " + metadata['official_panel']['ADM'] + "\n")
            f.write("  MUS: " + metadata['official_panel']['MUS'] + "\n")
            f.write("  PER: " + metadata['official_panel']['PER'] + "\n")
            f.write("  SNG: " + metadata['official_panel']['SNG'] + "\n\n")
            
            f.write("Awards:\n")
            for award in metadata['awards']:
                f.write("  - Award: " + award['award'] + "\n")
                f.write("    Winner: " + award['winner'] + "\n")
            f.write("\n")
            
            f.write("Draw:\n")
            for draw in metadata['draw']:
                f.write("  - Number: " + draw['number'] + "\n")
                f.write("    Group: " + draw['group'] + "\n")
            if metadata['mic_tester']:
                f.write("  - Mic Tester: " + metadata['mic_tester'] + "\n")
            f.write("\n")
            
            f.write("Evaluation Only:\n")
            for group in metadata['evaluation_only']:
                f.write("  - " + group + "\n")
            f.write("\n")
            
            f.write("Published:\n")
            f.write("  Name: " + metadata['published']['name'] + "\n")
            f.write("  Date: " + metadata['published']['date'] + "\n\n")
            
            f.write("Footnotes:\n")
            for footnote in metadata['footnotes']:
                f.write("  - " + footnote + "\n")
            f.write("\n")
            
            f.write("Disqualifications:\n")
            for disqualification in metadata['disqualifications']:
                f.write("  - " + disqualification + "\n")
                    
        print(f"Metadata saved to {txt_output_path}")
        return metadata
    except Exception as e:
        print(f"Error extracting metadata from PDF: {e}")
        return metadata

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

def create_tremper_table(json_path, tremper_output_path):
    """
    Create a Tremper Table format - specifically requested by Steve Tremper as part of his management
    of the harmonet score archive ranked summaries. Outputs group name and total score separated by tabs.
    
    Args:
        json_path (str): Path to the input JSON file
        tremper_output_path (str): Path to save the Tremper Table formatted file
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Create list to hold all rows
    rows = []
    
    for group_data in data:
        group_name = group_data['group_details']['group']
        group_representing = group_data['group_details'].get('representing', '')  # Default to empty string if not found
        group_district = group_data['group_details'].get('district', '')  # Default to empty string if not found
        percent_avg = group_data['combined_total_scores']['Total']
        on_stage = group_data['group_details'].get('on_stage', '')  # Default to empty string if not found
        total_points = group_data['combined_total_scores']['Points']
        rows.append({
            'group': group_name,
            'representing': group_representing,
            'district': group_district,
            'total_score': total_points,
            'on_stage': on_stage,
            'percent_avg': percent_avg
        })
    
    # Sort by total score in descending order
    rows.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Write to tab-separated file
    with open(tremper_output_path, 'w', encoding='utf-8') as f:
        f.write("Group\tRepresenting\tDistrict\tTotal Score\tOn Stage\tPercent Avg\n")
        for row in rows:
            f.write(f"{row['group']}\t{row['representing']}\t{row['district']}\t{row['total_score']}\t{row['on_stage']}\t{row['percent_avg']}\n")
    
    print(f"Tremper Table format saved to {tremper_output_path}")

def convert_scoresheet(pdf_path: str, formats: list[str], metadataOnly: bool = False) -> dict[str, str]:
    base_path = pdf_path.rsplit('.', 1)[0]
    paths = {}

    # Extract metadata to a separate text file
    txt_path = f"{base_path}_metadata.txt"
    metadata = extract_metadata(pdf_path, txt_path)
    paths["metadata"] = txt_path

    if metadataOnly:
        return paths

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

    if "tremper" in formats:
        tremper_path = f"{base_path}_tremper.txt"
        if "json" not in paths:
            json_path = f"{base_path}.json"
            if "csv" not in paths:
                csv_path = f"{base_path}.csv"
                extract_tables(pdf_path, csv_path)
            parse_table(csv_path, json_path)
        create_tremper_table(json_path, tremper_path)
        paths["tremper"] = tremper_path

    return paths

def extract_scores(row):
    """
    Extract scores from a row using the standard column names.
    Returns a dictionary with MUS, PER, SNG, and Total scores.
    """
    scores = {}
    for score_type in ['MUS', 'PER', 'SNG', 'Total']:
        if score_type in row:
            try:
                scores[score_type] = float(row[score_type])
            except (ValueError, TypeError):
                print(f"Warning: Could not convert {score_type} score to float: {row[score_type]}")
                scores[score_type] = 0.0
        else:
            print(f"Warning: Could not find {score_type} score in columns: {row.keys()}")
            scores[score_type] = 0.0
    
    return scores

def parse_table(csv_path, json_path):
    data = []
    current_group = None
    current_round = 'Finals'  # Default to Finals
    group_details = []  # Store all details for current group
    
    # Read the CSV file with pandas to handle the BOM
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    # Clean column names
    df.columns = [clean_column_name(col) for col in df.columns]
    
    # Convert DataFrame to list of dictionaries
    rows = df.to_dict('records')
    
    for row in rows:
        # Try to find the group column
        group_col = 'Group'
        
        if not group_col:
            print("Warning: Could not find group column. Available columns:", row.keys())
            continue
            
        # Check if this row starts a new group
        if row[group_col] and re.match(r'\d+\.', str(row[group_col])):
            # If we have a current group, process its details before starting a new one
            if current_group:
                process_group_details(group_details, current_group)
                data.append(current_group)
                group_details = []  # Reset details for new group
            
            # Extract placement and group name
            group_parts = str(row[group_col]).split('. ', 1)
            placement = int(group_parts[0])
            group_name = group_parts[1].split(' (')[0]  # Remove district info if present
            group_district = group_parts[1].split(' (')[1].split(')')[0] if ' (' in group_parts[1] else None
            
            scores = extract_scores(row)
            
            current_group = {
                'group_details': {
                    'placement': placement,
                    'group': group_name,
                    'district': group_district
                },
                'combined_total_scores': scores,
                'rounds': {
                    'Finals': {
                        'scores': scores,
                        'songs': []
                    }
                }
            }
        else:
            # If we have a current group, collect this row's Group data
            if current_group and row[group_col]:
                details = str(row[group_col])
                group_details.append(details)
        
        # Process songs/rounds information
        song_col = 'Songs'
        
        if song_col and row[song_col]:
            if str(row[song_col]).startswith('Total: '):
                # Extract points from Total: 2000
                points_match = re.search(r'Total: (\d+)', row[song_col])
                if points_match:
                    current_group['combined_total_scores']['Points'] = int(points_match.group(1))
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
                # Only add the song if there's a valid title (i.e. not NaN)
                if row[song_col] and str(row[song_col]).strip() and not pd.isna(row[song_col]):
                    song_info = {
                        'title': row[song_col],
                        'scores': extract_scores(row)
                    }
                    current_group['rounds'][current_round]['songs'].append(song_info)

    # Process details for the last group
    if current_group:
        process_group_details(group_details, current_group)
        data.append(current_group)

    # Write to JSON file
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"JSON file saved to {json_path}")

def process_group_details(details_list, group_dict):
    """Process all collected details for a group"""
    if not details_list:
        return
            
    # Combine all details into a single string
    full_details = ' '.join(details_list)
    
    # Check if this is a chorus (has Dir(s):) or quartet
    if 'Dir(s):' in full_details:
        # Chorus case - only extract chorus fields
        # Extract representing (everything before first parenthesis)
        if '(' in full_details:
            group_dict['group_details']['representing'] = full_details.split('(')[0].strip()
        
        # Extract directors
        dirs_text = full_details.split('Dir(s):')[1].split(';')[0].strip()
        group_dict['group_details']['directors'] = dirs_text
        
        # Extract on_stage count
        if 'OnStage:' in full_details:
            try:
                on_stage_text = full_details.split('OnStage:')[1].strip()
                group_dict['group_details']['on_stage'] = int(on_stage_text)
            except (ValueError, IndexError):
                pass
    else:
        # Quartet case - only extract quartet fields
        # Extract district (everything before first open parenthesis)
        if '(' in full_details:
            group_dict['group_details']['district'] = full_details.split('(')[0].strip()
        
        # Extract members (everything after close parenthesis)
        if ')' in full_details:
            members_text = full_details.split(')')[1].strip()
            # Remove " nan " patterns and end-of-string "nan"
            members_text = members_text.replace(' nan ', ' ').rstrip(' nan')
            if members_text:  # Only add if there's actual content
                group_dict['group_details']['members'] = members_text

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse a barbershop scoresheet PDF into various formats.")
    parser.add_argument("--input", "-i", required=True, help="Path to the input PDF file.")
    parser.add_argument("--formats", "-f", nargs="+", choices=["csv", "json", "pivot", "metadata", "tremper"], default=["csv", "json", "pivot", "metadata", "tremper"],
                        help="Output formats to generate (default: all)")

    args = parser.parse_args()
    

    convert_scoresheet(args.input, args.formats)


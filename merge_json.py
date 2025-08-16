import json
import os

# Paths to the two directories containing JSON files
old_path = r"C:\Users\xstor\OneDrive\Desktop\CSUN Spring 2025\Python Projects\Discord Bot\Discord Bot"
new_path = r"C:\Users\xstor\OneDrive\Desktop\CSUN Spring 2025\Python Projects\Discord Bot"

def merge_json_files(server_id):
    """Merges two JSON files for the same server into one."""
    old_file = os.path.join(old_path, f"{server_id}.json")
    new_file = os.path.join(new_path, f"{server_id}.json")

    # Load old JSON data
    old_data = {}
    if os.path.exists(old_file):
        with open(old_file, "r") as file:
            try:
                old_data = json.load(file)
            except json.JSONDecodeError:
                print(f"Error reading {old_file}")

    # Load new JSON data
    new_data = {}
    if os.path.exists(new_file):
        with open(new_file, "r") as file:
            try:
                new_data = json.load(file)
            except json.JSONDecodeError:
                print(f"Error reading {new_file}")

    # Merge the data (prioritize new data but keep missing fields from old data)
    merged_data = new_data.copy()
    for user_id, user_info in old_data.items():
        if user_id not in merged_data:
            merged_data[user_id] = user_info
        else:
            # Merge subfields (stats, birthdays, teams, etc.)
            for key, value in user_info.items():
                if key not in merged_data[user_id]:
                    merged_data[user_id][key] = value

    # Save the merged file back into the new directory
    with open(new_file, "w") as file:
        json.dump(merged_data, file, indent=4)

    print(f"Merged data saved to {new_file}")

# Get a list of server JSON files in the old directory
server_files = [f for f in os.listdir(old_path) if f.endswith(".json")]

# Merge each server's JSON file
for file in server_files:
    server_id = file.replace(".json", "")
    merge_json_files(server_id)

print("✅ All JSON files have been merged successfully!")

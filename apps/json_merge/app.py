import streamlit as st
import json
import io

def merge_json(json1, json2):
    """ Recursively merge two JSON objects (dictionaries) and track added items. """
    new_chats = []
    
    def merge_dict(dict1, dict2, path=[]):
        """ Helper to merge two dictionaries. """
        for k in dict2:
            if k in dict1:
                if isinstance(dict1[k], dict) and isinstance(dict2[k], dict):
                    merge_dict(dict1[k], dict2[k], path + [str(k)])
                elif isinstance(dict1[k], list) and isinstance(dict2[k], list):
                    existing_items = set(item['id'] for item in dict1[k])
                    for item in dict2[k]:
                        if 'id' in item and item['id'] not in existing_items:
                            dict1[k].append(item)
                            if 'chats' in path:
                                new_chats.append(item)
                else:
                    dict1[k] = dict2[k]
            else:
                dict1[k] = dict2[k]
                if 'chats' in path and isinstance(dict2[k], list):
                    new_chats.extend(dict2[k])
    
    merge_dict(json1, json2)
    return new_chats


def main():
    st.title("JSON Merger with New Items Tracker")
    st.write("Upload two JSON files to merge them and see which chats were added.")

    json_file1 = st.file_uploader("Choose the first JSON file", type="json")
    json_file2 = st.file_uploader("Choose the second JSON file", type="json")

    if json_file1 and json_file2:
        # Load the JSON data from the uploaded files
        content1 = json_file1.read().decode("utf-8")
        content2 = json_file2.read().decode("utf-8")

        try:
            json_data1 = json.loads(content1)
            json_data2 = json.loads(content2)

            # Merge the two JSON objects
            added_chats = merge_json(json_data1, json_data2)

            # Display the merged JSON
            st.json(json_data1)

            # Create a downloadable file for the merged JSON
            download_file = io.BytesIO()
            download_file.write(json.dumps(json_data1, indent=4).encode('utf-8'))
            download_file.seek(0)

            st.download_button(
                label="Download merged JSON",
                data=download_file,
                file_name="merged.json",
                mime="application/json"
            )

            # Display any new chats added
            if added_chats:
                st.write("New chats added:")
                for chat in added_chats:
                    st.write(f"- ID: {chat['id']}, Title: {chat.get('title', 'No title')}")

        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON data: {e}")

if __name__ == "__main__":
    main()

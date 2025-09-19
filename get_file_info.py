import sqlite3

conn = sqlite3.connect('files.db')
cursor = conn.cursor()
cursor.execute("SELECT id, filename, file_id, folder FROM files WHERE filename != '.folder_marker' LIMIT 1;")
file_data = cursor.fetchone()
if file_data:
    print(f"ID: {file_data[0]}, Filename: {file_data[1]}, File ID: {file_data[2]}, Folder: {file_data[3]}")
else:
    print("No files found in the database.")
conn.close()
import os
import logging
import datetime
import pytz
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

# Set up logging
logging.basicConfig(filename='back.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

# Authentication
def authenticate():
    token_path = '/app/credentials/token.json'
    
    SCOPES = ["https://www.googleapis.com/auth/drive"]

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    else:
        raise Exception("Credentials not found.")
    return build('drive', 'v3', credentials=creds)

# File Upload Logic
def upload_file(service, filename, path):
    folder_id = "1BGtSt-NsLuvO8DnL9YoFWMGFx6aE1is0"
    file_path = os.path.join(path, filename)
    media = MediaFileUpload(file_path)

    logging.info(f"Checking if file '{filename}' exists and needs updating...")
    query = f"name='{filename}' and parents='{folder_id}'"
    response = service.files().list(q=query, spaces='drive', fields='nextPageToken, files(id, name, modifiedTime)').execute()

    if not response['files']:
        # File not found, upload as new
        logging.info(f"File '{filename}' not found. Uploading new file...")
        file_metadata = {'name': filename, 'parents': [folder_id]}
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info(f"New file '{filename}' created with ID {file.get('id')}")

    else:
        file = response.get('files', [])[0]
        print("file: ",file)
        remote_modified_time = datetime.datetime.strptime(file['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
        remote_modified_time =  remote_modified_time.astimezone(pytz.timezone('Asia/Kolkata'))
        local_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        local_modified_time = pytz.utc.localize(local_modified_time).astimezone(pytz.timezone('Asia/Kolkata'))

        print("local:",local_modified_time,"remote:", remote_modified_time)

        if local_modified_time > remote_modified_time:  # Local file is newer
            logging.info(f"File '{filename}' has been modified. Updating...")

            logging.info(f"Deleting older File '{filename}'...")
            service.files().delete(fileId=file['id']).execute()

            file_metadata = {'name': filename, 'parents': [folder_id]}
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            logging.info(f"New file '{filename}' created with ID {file.get('id')}")
            logging.info(f"File '{filename}' updated.")
        else:
            logging.info(f"File '{filename}' is up-to-date. No update needed.")

# Main Execution
def main():
    path = "backupFiles/"  # Your local folder to backup
    service = authenticate()

    for item in os.listdir(path):
        logging.info(f"Processing file '{item}'...")
        try:
            upload_file(service, item, path)
        except Exception as e:
            logging.error(f"Error occurred while uploading file '{item}': {str(e)}")
    logging.info("Backup process completed.")

if __name__ == '__main__':
    main()

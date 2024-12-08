from flask import Flask, request, jsonify
from flask_cors import CORS

import os
import json
# from werkzeug.utils import secure_filename
import uuid
# import snowflake.connector
import os
# from dotenv import load_dotenv
import requests
import base64
import json
from datetime import datetime
from dotenv import load_dotenv

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'blob'}

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://main.d2bkr9t6m7ypy2.amplifyapp.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Define data directory path
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
BLACKLIST_FILE = os.path.join(DATA_DIR, 'blacklist.json')
RESPONSE_FILE = os.path.join(DATA_DIR, 'response.json')

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize blacklist.json if it doesn't exist
if not os.path.exists(BLACKLIST_FILE):
    with open(BLACKLIST_FILE, 'w') as f:
        json.dump({"blacklist": []}, f)

# Temporary storage (replace with database in production)
users = {}
profiles = {}

def allowed_file(file):
    return file and '.' in file.filename and \
           file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def encode_image(image_path):
    """Encodes an image file into base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def validate_id(document_image, face_image=None):
    '''
    This function validates a provided ID, along with an optional image of the persons face, 
    and saves the results.
    :param document_image: The path to an image of the ID to validate
    :param face_image: Optional - a path to an image of the person to validate the ID of
    :param output_file: Optional - the location to save the results of the ID validation
    '''
    # Load environment variables
    load_dotenv()
    
    # Get API key and profile ID from environment variables
    api_key = os.getenv('ID_ANALYZER_API_KEY')
    profile_id = os.getenv('ID_ANALYZER_PROFILE_ID')
    
    if not api_key or not profile_id:
        raise ValueError("API key or Profile ID not found in environment variables")
        
    api_url = "https://api2.idanalyzer.com/scan"

    document_base64 = encode_image(document_image)

    # Build the payload
    payload = {
        "profile": profile_id,
        "document": document_base64
    }

    if face_image: # If an image of the face is provided, add it to the payload
        payload["face"] = encode_image(face_image)

    # Set headers
    headers = {
        'X-API-KEY': api_key,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    # Send the POST request
    response = requests.post(api_url, headers=headers, data=json.dumps(payload))
    result = response.json()
    
    # Add validation checks
    validation_messages = []
    
    if result and 'data' in result:
        # Check age - make sure we're getting a valid number
        age_data = result['data'].get('age', [{}])[0].get('value', '')
        if age_data:
            try:
                age = int(float(age_data))  # Convert to float first in case it comes as decimal
                if age < 19:
                    validation_messages.append({
                        'type': 'underage',
                        'message': f'User is under 19 years old (Age: {age})'
                    })
            except (ValueError, TypeError):
                print(f"Could not parse age value: {age_data}")
                pass

        # Check expiry with better date handling
        expiry = result['data'].get('expiry', [{}])[0].get('value', '')
        if expiry:
            try:
                # Handle different possible date formats
                for date_format in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y']:
                    try:
                        expiry_date = datetime.strptime(expiry, date_format)
                        if expiry_date < datetime.now():
                            validation_messages.append({
                                'type': 'expired',
                                'message': f'ID expired on {expiry}'
                            })
                        break
                    except ValueError:
                        continue
            except Exception as e:
                print(f"Error processing expiry date: {e}")
                pass

    result['validationMessages'] = validation_messages
    return result


@app.route('/api/blacklist-individual', methods=['POST'])
def blacklist_individual():
    if 'idPhoto' not in request.files:
        return jsonify({'error': 'No ID provided'}), 400
    
    idPhotoFile = request.files['idPhoto']
    user_id = str(uuid.uuid4())
    user_id_file_path =  os.path.join(app.config['UPLOAD_FOLDER'], f"{user_id}_id.png")
    idPhotoFile.save(user_id_file_path)

    response = validate_id(user_id_file_path)

    data = response['data']
    
    full_name = data.get('fullName', [{}])[0].get('value', '')

    # Get date of birth
    dob = data.get('dob', [{}])[0].get('value', '')
    
    # Get age from response or calculate it
    age = data.get('age', [{}])[0].get('value', '')

    with open(BLACKLIST_FILE, 'r') as file:
        blacklist = json.load(file).get("blacklist")

    blacklist.append({
        "name": full_name,
        "dateOfBirth": dob,
        "age": age,
    })
    
    with open(BLACKLIST_FILE, 'w') as file:
        json.dump({"blacklist": blacklist}, file, indent=4)

    return jsonify({'message': f'{full_name} has been added to the blacklist'}), 200


@app.route('/api/upload-photo', methods=['POST'])
def upload_photo():
    if 'idPhoto' not in request.files:
        return jsonify({'error': 'No ID provided'}), 400
    
    idPhotoFile = request.files['idPhoto']
    facePhotoFile = request.files.get('facePhoto', None)
    user_id = str(uuid.uuid4())
    
    if allowed_file(idPhotoFile):
        # Save with user ID in filename for uniqueness
        user_id_file_path =  os.path.join(app.config['UPLOAD_FOLDER'], f"{user_id}_id.png")
        idPhotoFile.save(user_id_file_path)
        
        try:
            if allowed_file(facePhotoFile): # If face is provided and is valid, send it to idanalyzer
                user_face_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{user_id}_face.png")
                facePhotoFile.save(user_face_file_path)
                response = validate_id(user_id_file_path, face_image=user_face_file_path)
            else: # Otherwise, just send the ID
                response = validate_id(user_id_file_path)
            
            # Save response for debugging (optional - you might want to remove this in production)
            with open(RESPONSE_FILE, 'w') as f:
                json.dump(response, f, indent=2)
            
            # Extract relevant information from response
            if response and 'data' in response:
                data = response['data']
                
                # Get full name
                full_name = data.get('fullName', [{}])[0].get('value', '')

                # Get date of birth
                dob = data.get('dob', [{}])[0].get('value', '')
                
                # Get age from response or calculate it
                age = data.get('age', [{}])[0].get('value', '')
                
                # Check if document is valid
                is_valid = response.get('decision', '').lower() == 'accept'

                expiry = data.get('expiry', [{}])[0].get('value', '')
                
                # Get warnings with medium or higher severity
                warnings = [
                    {
                        'code': w.get('code', ''),
                        'description': w.get('description', ''),
                        'severity': w.get('severity', '')
                    }
                    for w in response.get('warning', [])
                    if w.get('severity', '').lower() in ['medium', 'high', 'critical']
                ]

                    
                with open(BLACKLIST_FILE, 'r') as f:
                    blacklist_data = json.load(f)
                    blacklisted_users = blacklist_data.get("blacklist", [])
                    for entry in blacklisted_users:
                        if entry["name"] == full_name:
                            response["validationMessages"].append({
                        'type': 'blacklist',
                        'message': f'{full_name} has been blacklisted'
                    })

                return jsonify({
                    "isValid": is_valid,
                    "details": {
                        "name": full_name,
                        "dateOfBirth": dob,
                        "age": age,
                        "expiryDate": expiry
                    },
                    "warnings": warnings,
                    "validationMessages": response.get('validationMessages', [])  # Include validation messages
                })
            else:
                return jsonify({
                    "isValid": False,
                    "error": "Failed to extract information from ID"
                }), 400

        except Exception as e:
            raise e
            return jsonify({
                "isValid": False,
                "error": str(e)
            }), 500
        
        finally:
            #Clean up the uploaded file
            if os.path.exists(user_id_file_path):
                os.remove(user_id_file_path)
            # if os.path.exists(user_face_file_path):
            #     os.remove(user_face_file_path)
    
    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
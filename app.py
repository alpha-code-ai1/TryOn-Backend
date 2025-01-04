import base64
import os
from flask import Flask, request, jsonify
from gradio_client import Client, file
from werkzeug.utils import secure_filename
from flask_cors import CORS  # Add this for cross-origin support
from os import environ
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize Gradio Client
client = Client("Nymbo/Virtual-Try-On")

# Create a folder to save uploaded files temporarily
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Add after app initialization
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def image_to_base64(image_path):
    """Convert image to base64 encoded string"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error converting image to base64: {e}")
        return None

@app.route('/')
def index():
    return "Virtual Try-On Backend is running! Use the /tryon endpoint to make predictions."

@app.route('/tryon', methods=['POST'])
def try_on():
    # Add API key validation
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != os.environ.get('API_KEY'):
        return jsonify({"error": "Invalid API key"}), 401
    
    try:
        # Get uploaded files
        if 'background_image' not in request.files or 'garment_image' not in request.files:
            return jsonify({"error": "Missing image files"}), 400

        background_file = request.files['background_image']
        garment_file = request.files['garment_image']
        garment_description = request.form.get('garment_description', 'A stylish garment')

        # Save files temporarily
        background_path = os.path.join(UPLOAD_FOLDER, secure_filename(background_file.filename))
        garment_path = os.path.join(UPLOAD_FOLDER, secure_filename(garment_file.filename))
        background_file.save(background_path)
        garment_file.save(garment_path)

        # Log file details to verify they are received
        print(f"Saved background image at: {background_path}")
        print(f"Saved garment image at: {garment_path}")

        # Call the Gradio Client API
        result = client.predict(
            dict={
                "background": file(background_path),
                "layers": [],
                "composite": None
            },
            garm_img=file(garment_path),
            garment_des=garment_description,
            is_checked=True,
            is_checked_crop=False,
            denoise_steps=30,
            seed=42,
            api_name="/tryon"
        )

        output_image_path, masked_image_path = result

        # Log result paths
        print(f"Output image path: {output_image_path}")
        print(f"Masked image path: {masked_image_path}")

        # Convert images to base64
        output_image_base64 = image_to_base64(output_image_path)
        masked_image_base64 = image_to_base64(masked_image_path)

        # Clean up uploaded files
        os.remove(background_path)
        os.remove(garment_path)

        # Return base64 encoded images
        return jsonify({
            "output_image": output_image_base64,
            "masked_image": masked_image_base64
        })

    except Exception as e:
        # Log and return any exceptions
        print(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
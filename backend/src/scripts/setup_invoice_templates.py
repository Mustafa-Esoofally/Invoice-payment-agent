"""Script to set up invoice templates in Firebase Storage."""

import os
import sys
from pathlib import Path
from typing import Dict, List
import shutil
from firebase_admin import initialize_app, credentials, storage, get_app
import json
import traceback

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

def setup_templates_directory() -> str:
    """Create and populate the templates directory."""
    # Create templates directory if it doesn't exist
    templates_dir = Path(current_dir) / "invoice_templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Copy template files from reference if they exist
    reference_dir = Path(parent_dir).parent / "reference"
    if reference_dir.exists():
        print(f"Looking for templates in reference directory: {reference_dir}")
        # Look for PDF files in the reference directory and its subdirectories
        for pdf_file in reference_dir.rglob("*.pdf"):
            if any(template_name in pdf_file.name for template_name in [
                "Black White Minimalist Modern Business Invoice.pdf",
                "Simple Minimalist Aesthetic Business Invoice.pdf"
            ]):
                target_path = templates_dir / pdf_file.name
                print(f"Copying template: {pdf_file.name}")
                shutil.copy2(pdf_file, target_path)
                print(f"✓ Copied to: {target_path}")
    else:
        print(f"Reference directory not found: {reference_dir}")
        print("Creating placeholder template files...")
        # Create placeholder files if they don't exist
        template_files = [
            "Black White Minimalist Modern Business Invoice.pdf",
            "Simple Minimalist Aesthetic Business Invoice.pdf"
        ]
        
        for template in template_files:
            template_path = templates_dir / template
            if not template_path.exists():
                # Create a simple PDF file
                with open(template_path, 'w') as f:
                    f.write(f"Sample invoice template: {template}")
                print(f"Created placeholder file: {template}")
    
    return str(templates_dir.absolute())

def upload_templates_to_firebase(templates_dir: str) -> List[Dict]:
    """Upload invoice templates to Firebase Storage."""
    try:
        # Initialize Firebase if not already initialized
        try:
            firebase_app = get_app()
            print("Using existing Firebase app")
        except ValueError:
            cred_path = Path(parent_dir) / "payman-agent-render-firebase-adminsdk-fbsvc-76639f1307.json"
            if not cred_path.exists():
                raise FileNotFoundError(f"Firebase credentials not found at {cred_path}")
            
            # Use the correct bucket name
            bucket_name = "payman-agent-render.firebasestorage.app"
            
            cred = credentials.Certificate(str(cred_path))
            firebase_app = initialize_app(cred, {
                'storageBucket': bucket_name
            })
            print(f"Initialized new Firebase app with bucket: {bucket_name}")
        
        # Get storage bucket
        bucket = storage.bucket()
        print(f"Connected to bucket: {bucket.name}")
        
        # List of uploaded files
        uploaded_files = []
        
        # Upload each template
        templates_path = Path(templates_dir)
        for template_file in templates_path.glob("*.pdf"):
            try:
                # Create blob with public read access
                destination_blob_name = f"templates/{template_file.name}"
                blob = bucket.blob(destination_blob_name)
                
                # Upload the file
                print(f"\nUploading {template_file.name}...")
                blob.upload_from_filename(str(template_file))
                
                # Make the blob publicly readable
                blob.make_public()
                
                # Get the public URL
                url = blob.public_url
                
                # Store upload info
                uploaded_files.append({
                    "name": template_file.name,
                    "url": url,
                    "size": os.path.getsize(template_file)
                })
                
                print(f"✓ Uploaded {template_file.name}")
                print(f"  URL: {url}")
                print(f"  Size: {os.path.getsize(template_file):,} bytes")
                
            except Exception as e:
                print(f"❌ Error uploading {template_file.name}: {str(e)}")
                traceback.print_exc()
        
        return uploaded_files
        
    except Exception as e:
        print(f"❌ Error in upload_templates_to_firebase: {str(e)}")
        traceback.print_exc()
        return []

def update_invoice_templates(uploaded_files: List[Dict]):
    """Update the invoice templates in generate_invoice_data.py."""
    if not uploaded_files:
        print("No files were uploaded, skipping template update")
        return
    
    try:
        # Read the current file
        script_path = Path(parent_dir) / "generate_invoice_data.py"
        with open(script_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find the INVOICE_FILES section
        start_idx = -1
        end_idx = -1
        for i, line in enumerate(lines):
            if "INVOICE_FILES = [" in line:
                start_idx = i + 1
            elif start_idx >= 0 and "]" in line:
                end_idx = i
                break
        
        if start_idx < 0 or end_idx < 0:
            raise ValueError("Could not find INVOICE_FILES section in generate_invoice_data.py")
        
        # Create new template entries
        new_templates = []
        for file in uploaded_files:
            new_templates.append(f"""    {{
        "url": "{file['url']}",
        "name": "{file['name']}"
    }}""")
        
        # Join with commas
        template_text = ",\n".join(new_templates)
        
        # Replace the old section with new templates
        new_lines = lines[:start_idx] + [template_text + "\n"] + lines[end_idx:]
        
        # Write back to file
        with open(script_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print("\n✓ Updated generate_invoice_data.py with new template URLs")
        
    except Exception as e:
        print(f"❌ Error updating generate_invoice_data.py: {str(e)}")
        traceback.print_exc()

def main():
    """Main function to set up invoice templates."""
    print("\n🚀 Setting up invoice templates")
    print("=" * 50)
    
    # Set up templates directory
    print("\n📁 Setting up templates directory...")
    templates_dir = setup_templates_directory()
    print(f"✓ Templates directory: {templates_dir}")
    
    # Upload templates to Firebase Storage
    print("\n☁️ Uploading templates to Firebase Storage...")
    uploaded_files = upload_templates_to_firebase(templates_dir)
    
    if uploaded_files:
        print(f"\n✅ Successfully uploaded {len(uploaded_files)} templates")
        
        # Update generate_invoice_data.py
        print("\n📝 Updating invoice template data...")
        update_invoice_templates(uploaded_files)
        
        print("\n🎉 Setup complete!")
    else:
        print("\n❌ No templates were uploaded")

if __name__ == "__main__":
    main() 
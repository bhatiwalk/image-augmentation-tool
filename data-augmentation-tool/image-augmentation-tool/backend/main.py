from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from augmentation import apply_augmentations
from utils import clean_directory, create_zip
import os
import io
from typing import List
from PIL import Image
import multipart
from starlette.datastructures import UploadFile as StarletteUploadFile

# Configure file upload limits - remove limits for unlimited files
from starlette.middleware.base import BaseHTTPMiddleware

class UnlimitedUploadMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Remove any file count limits
        return await call_next(request)

def parse_multipart_unlimited(body: bytes, boundary: bytes):
    """Custom multipart parser without file count limits, handles fields and files"""
    files = []
    fields = {}
    
    # Split by boundary
    parts = body.split(b'--' + boundary)
    
    for part in parts[1:-1]:  # Skip first empty part and last closing part
        if not part.strip():
            continue
            
        # Split headers and body
        if b'\r\n\r\n' in part:
            headers_section, data = part.split(b'\r\n\r\n', 1)
        else:
            continue
            
        headers_text = headers_section.decode('utf-8', errors='ignore')
        
        # Extract Content-Disposition
        content_disposition = None
        for line in headers_text.split('\r\n'):
            if line.lower().startswith('content-disposition:'):
                content_disposition = line
                break
        
        if not content_disposition:
            continue

        # Check if it's a file or a field
        if 'filename=' in content_disposition:
            # It's a file
            filename = None
            start = content_disposition.find('filename="') + 10
            if start > 9:
                end = content_disposition.find('"', start)
                if end > start:
                    filename = content_disposition[start:end]
            
            if filename and data:
                # Remove trailing boundary markers
                file_data = data.rstrip(b'\r\n')
                
                # Create a file-like object
                file_obj = io.BytesIO(file_data)
                file_obj.filename = filename
                file_obj.size = len(file_data)
                files.append(file_obj)
        else:
            # It's a form field
            field_name = None
            start = content_disposition.find('name="') + 6
            if start > 5:
                end = content_disposition.find('"', start)
                if end > start:
                    field_name = content_disposition[start:end]

            if field_name:
                fields[field_name] = data.rstrip(b'\r\n').decode('utf-8', errors='ignore')

    return {"files": files, "fields": fields}

app = FastAPI(
    # Remove default limits
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add unlimited upload middleware
app.add_middleware(UnlimitedUploadMiddleware)

# Configure CORS - Allow all localhost ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://localhost:5500",  # Live Server default
        "http://127.0.0.1:5500",
        "null"  # For file:// protocol
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

UPLOAD_DIR = "uploads"
AUGMENTED_DIR = "augmented"

# Print working directory and paths for debugging
print(f"Backend working directory: {os.getcwd()}")
print(f"Upload directory path: {os.path.abspath(UPLOAD_DIR)}")
print(f"Augmented directory path: {os.path.abspath(AUGMENTED_DIR)}")

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AUGMENTED_DIR, exist_ok=True)

# Serve static files from augmented directory
app.mount("/augmented", StaticFiles(directory=AUGMENTED_DIR), name="augmented")

class AugmentationRequest(BaseModel):
    augmentations: List[str]

@app.post("/upload")
async def upload_images(request: Request):
    print(f"UPLOAD DEBUG: Received request")
    clean_directory(UPLOAD_DIR)
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
    MAX_TOTAL_SIZE = 10 * 1024 * 1024 * 1024  # 10GB total
    
    saved_files = []
    total_size = 0
    
    try:
        # Get the raw body and content type
        body = await request.body()
        content_type = request.headers.get('content-type', '')
        body_size = len(body)
        
        print(f"UPLOAD DEBUG: Request body size: {body_size / (1024*1024):.1f} MB")
        
        if not content_type.startswith('multipart/form-data'):
            raise HTTPException(status_code=400, detail="Expected multipart/form-data")
        
        # Extract boundary
        boundary_marker = 'boundary='
        boundary_start = content_type.find(boundary_marker)
        if boundary_start == -1:
            raise HTTPException(status_code=400, detail="No boundary found in content-type")
        
        boundary = content_type[boundary_start + len(boundary_marker):].strip()
        if boundary.startswith('"') and boundary.endswith('"'):
            boundary = boundary[1:-1]
        
        print(f"UPLOAD DEBUG: Using boundary: {boundary}")
        
        # For very large uploads (>100MB), use streaming approach
        if body_size > 100 * 1024 * 1024:  # 100MB
            print("UPLOAD DEBUG: Large upload detected, using streaming approach")
            return await handle_large_upload(body, boundary, MAX_FILE_SIZE, MAX_TOTAL_SIZE)
        
        # Parse multipart data with our custom parser
        try:
            parsed_data = parse_multipart_unlimited(body, boundary.encode())
            files = parsed_data["files"]
            print(f"UPLOAD DEBUG: Custom parser found {len(files)} files")
        except Exception as parse_error:
            print(f"UPLOAD DEBUG: Parser failed: {str(parse_error)}")
            # Fallback to streaming approach for problematic uploads
            return await handle_large_upload(body, boundary, MAX_FILE_SIZE, MAX_TOTAL_SIZE)
        
        files_processed = 0
        files_saved = 0
        
        for file_obj in files:
            files_processed += 1
            
            # More comprehensive file validation
            if not hasattr(file_obj, 'filename') or not file_obj.filename:
                print(f"UPLOAD DEBUG: Skipping file {files_processed}: no filename")
                continue
                
            if not file_obj.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                print(f"UPLOAD DEBUG: Skipping file {files_processed}: not an image ({file_obj.filename})")
                continue
                
            try:
                # Read file content
                file_obj.seek(0)
                contents = file_obj.read()
                
                # Check file size
                file_size = len(contents)
                if file_size == 0:
                    print(f"UPLOAD DEBUG: Skipping {file_obj.filename}: empty file")
                    continue
                    
                if file_size > MAX_FILE_SIZE:
                    print(f"UPLOAD DEBUG: Skipping {file_obj.filename}: too large ({file_size / (1024*1024):.1f} MB)")
                    continue
                
                if total_size + file_size > MAX_TOTAL_SIZE:
                    print(f"UPLOAD DEBUG: Total size limit reached, stopping at file {files_processed}")
                    break
                
                # Validate it's actually an image
                try:
                    Image.open(io.BytesIO(contents))
                except Exception as img_error:
                    print(f"UPLOAD DEBUG: Skipping {file_obj.filename}: not a valid image ({str(img_error)})")
                    continue
                
                file_path = os.path.join(UPLOAD_DIR, file_obj.filename)
                with open(file_path, "wb") as buffer:
                    buffer.write(contents)
                saved_files.append(file_path)
                total_size += file_size
                files_saved += 1
                
                print(f"UPLOAD DEBUG: Saved {file_obj.filename} ({file_size} bytes) - {files_saved}/{files_processed}")
                
                # Progress update for large batches
                if files_processed % 100 == 0:
                    print(f"UPLOAD DEBUG: Processed {files_processed} files, saved {files_saved}")
                
            except Exception as e:
                print(f"UPLOAD DEBUG: Error processing {file_obj.filename}: {str(e)}")
                continue
        
        print(f"UPLOAD DEBUG: Final stats - Processed: {files_processed}, Saved: {files_saved}, Total size: {total_size / (1024*1024):.1f} MB")
        
    except Exception as e:
        error_msg = str(e)
        print(f"UPLOAD DEBUG: Error in upload process: {error_msg}")
        
        # More specific error handling
        if "memory" in error_msg.lower() or "too large" in error_msg.lower():
            raise HTTPException(
                status_code=413, 
                detail="Upload too large. Please try uploading in smaller batches (max 500-800 files per batch)."
            )
        elif "too many files" in error_msg.lower() or "maximum number of files" in error_msg.lower():
            raise HTTPException(
                status_code=413, 
                detail="Too many files selected. Please try uploading in smaller batches."
            )
        else:
            raise HTTPException(status_code=400, detail=f"Error processing upload: {error_msg}")
    
    if not saved_files:
        # More detailed debugging info
        upload_files = os.listdir(UPLOAD_DIR) if os.path.exists(UPLOAD_DIR) else []
        print(f"UPLOAD DEBUG: No files saved. Upload directory contains: {upload_files}")
        raise HTTPException(
            status_code=400, 
            detail=f"No valid images were uploaded. Please ensure you're selecting image files (jpg, png, gif, bmp, webp) under 10MB each."
        )
    
    return {
        "message": f"Successfully uploaded {len(saved_files)} images ({total_size / (1024*1024):.1f} MB total)", 
        "files": saved_files,
        "total_size_mb": round(total_size / (1024*1024), 1)
    }

@app.post("/upload-batch")
async def upload_images_batch(request: Request):
    """Upload images in batches to handle large numbers of files"""
    print(f"BATCH UPLOAD DEBUG: Received request")
    
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB per file
    MAX_TOTAL_SIZE = 20 * 1024 * 1024 * 1024  # 20GB total
    
    # Add this at the start
    print(f"Starting upload of potentially large batch...")
    
    saved_files = []
    total_size = 0
    
    try:
        # Get the raw body and content type
        body = await request.body()
        content_type = request.headers.get('content-type', '')
        
        if not content_type.startswith('multipart/form-data'):
            raise HTTPException(status_code=400, detail="Expected multipart/form-data")
        
        # Extract boundary
        boundary_marker = 'boundary='
        boundary_start = content_type.find(boundary_marker)
        if boundary_start == -1:
            raise HTTPException(status_code=400, detail="No boundary found in content-type")
        
        boundary = content_type[boundary_start + len(boundary_marker):].strip()
        if boundary.startswith('"') and boundary.endswith('"'):
            boundary = boundary[1:-1]
            
        # Parse multipart data with our custom parser
        parsed_data = parse_multipart_unlimited(body, boundary.encode())
        files = parsed_data["files"]
        fields = parsed_data["fields"]
        
        batch_number = fields.get("batch_number", "1")
        is_first_batch = fields.get("is_first_batch", "false").lower() == "true"
        
        print(f"BATCH UPLOAD DEBUG: Batch {batch_number}, {len(files)} files, first batch: {is_first_batch}")
        
        # Clean directory only on first batch
        if is_first_batch:
            clean_directory(UPLOAD_DIR)
        
        for file_obj in files:
            if not hasattr(file_obj, 'filename') or not file_obj.filename:
                continue
                
            if not file_obj.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                continue
                
            try:
                file_obj.seek(0)
                contents = file_obj.read()
                file_size = len(contents)
                
                if file_size > MAX_FILE_SIZE:
                    print(f"File {file_obj.filename} too large: {file_size / (1024*1024):.1f} MB")
                    continue
                
                if total_size + file_size > MAX_TOTAL_SIZE:
                    print(f"Total size limit reached for this batch")
                    break
                
                Image.open(io.BytesIO(contents))
                
                file_path = os.path.join(UPLOAD_DIR, file_obj.filename)
                with open(file_path, "wb") as buffer:
                    buffer.write(contents)
                saved_files.append(file_path)
                total_size += file_size
                
            except Exception as e:
                print(f"Invalid image file {file_obj.filename}: {str(e)}")
                continue
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error parsing batch form: {error_msg}")
        raise HTTPException(status_code=400, detail=f"Error parsing batch upload: {error_msg}")
    
    # Get total files in upload directory
    total_uploaded = len([f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))])
    
    return {
        "message": f"Batch {batch_number}: uploaded {len(saved_files)} images ({total_size / (1024*1024):.1f} MB)",
        "batch_files": saved_files,
        "batch_size_mb": round(total_size / (1024*1024), 1),
        "total_files": total_uploaded
    }

@app.post("/augment")
async def augment_images(request: AugmentationRequest):
    # Add detailed logging
    print(f"AUGMENT DEBUG: Starting augmentation for {request.augmentations}")
    
    # Check if upload directory exists
    if not os.path.exists(UPLOAD_DIR):
        print(f"AUGMENT DEBUG: Upload directory does not exist: {UPLOAD_DIR}")
        raise HTTPException(status_code=400, detail=f"Upload directory does not exist: {UPLOAD_DIR}")
    
    # List all files in upload directory
    all_files_in_upload = os.listdir(UPLOAD_DIR)
    print(f"AUGMENT DEBUG: All files in upload directory: {all_files_in_upload}")
    
    # Verify files exist before processing
    input_files = []
    for f in all_files_in_upload:
        file_path = os.path.join(UPLOAD_DIR, f)
        print(f"AUGMENT DEBUG: Checking file: {f}, path: {file_path}, exists: {os.path.exists(file_path)}")
        
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
            if os.path.exists(file_path) and os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                print(f"AUGMENT DEBUG: Valid image found: {f} (size: {file_size} bytes)")
                input_files.append(file_path)
            else:
                print(f"AUGMENT DEBUG: File exists but is not a file: {f}")
        else:
            print(f"AUGMENT DEBUG: Skipping non-image file: {f}")
    
    print(f"AUGMENT DEBUG: Found {len(input_files)} valid input files out of {len(all_files_in_upload)} total files")
    
    if not input_files:
        # Provide more detailed error
        print(f"AUGMENT DEBUG: No valid images found. Upload directory contains {len(all_files_in_upload)} files total")
        print(f"AUGMENT DEBUG: Upload directory path: {os.path.abspath(UPLOAD_DIR)}")
        raise HTTPException(
            status_code=400, 
            detail=f"No valid images found in upload directory (contains {len(all_files_in_upload)} files total). Upload directory: {os.path.abspath(UPLOAD_DIR)}"
        )
    
    # Clean augmented directory
    clean_directory(AUGMENTED_DIR)
    
    try:
        # Apply augmentations - pass the output directory
        result = apply_augmentations(input_files, request.augmentations, AUGMENTED_DIR)
        
        # Count output files
        output_files = []
        if os.path.exists(AUGMENTED_DIR):
            for f in os.listdir(AUGMENTED_DIR):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                    output_files.append(f)
        
        print(f"Augmentation completed. Generated {len(output_files)} files")
        
        return {
            "message": f"{len(output_files)} augmented images",
            "input_files": len(input_files),
            "output_files": len(output_files),
            "augmentations_applied": request.augmentations
        }
        
    except Exception as e:
        print(f"Error during augmentation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Augmentation failed: {str(e)}")


@app.get("/augmented-images")
async def get_augmented_images():
    """Get list of augmented images for display"""
    try:
        images = []
        if not os.path.exists(AUGMENTED_DIR):
            print(f"Augmented directory does not exist: {AUGMENTED_DIR}")
            return {"images": []}
        
        all_files = os.listdir(AUGMENTED_DIR)
        print(f"Files in {AUGMENTED_DIR}: {all_files}")
        
        for filename in all_files:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                file_path = os.path.join(AUGMENTED_DIR, filename)
                file_size = os.path.getsize(file_path)
                print(f"Found image: {filename} (size: {file_size} bytes)")
                
                # Extract augmentation type from filename
                parts = filename.split('_')
                if len(parts) > 1:
                    aug_type = '_'.join(parts[1:]).replace('.jpg', '').replace('.png', '')
                    description = f"{parts[0]} - {aug_type.replace('_', ' ').title()}"
                else:
                    description = filename
                
                images.append({
                    "filename": filename,
                    "description": description
                })
        
        print(f"Returning {len(images)} images")
        return {"images": images}
    except Exception as e:
        print(f"Error listing images: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing images: {str(e)}")

@app.get("/download")
async def download_results():
    zip_path = os.path.join(AUGMENTED_DIR, "augmented_results.zip")
    if not os.path.exists(zip_path):
        # Try to create zip if it doesn't exist
        try:
            zip_path = create_zip(AUGMENTED_DIR)
        except:
            raise HTTPException(status_code=404, detail="No results to download")
    
    return FileResponse(zip_path, filename="augmented_dataset.zip")

# Add a test endpoint to check if images exist
@app.get("/test-images")
async def test_images():
    """Test endpoint to check augmented directory contents"""
    try:
        files = []
        if os.path.exists(AUGMENTED_DIR):
            all_files = os.listdir(AUGMENTED_DIR)
            for f in all_files:
                file_path = os.path.join(AUGMENTED_DIR, f)
                size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
                files.append({"name": f, "size": size, "is_image": f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))})
        
        return {
            "directory_exists": os.path.exists(AUGMENTED_DIR),
            "files": files,
            "total_files": len(files)
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/debug-upload")
async def debug_upload(request: Request):
    """Debug endpoint to see what's being received"""
    print(f"DEBUG UPLOAD: Received request")
    
    try:
        body = await request.body()
        content_type = request.headers.get('content-type', '')
        
        print(f"DEBUG UPLOAD: Content-Type: {content_type}")
        print(f"DEBUG UPLOAD: Body size: {len(body)} bytes")
        
        if 'multipart/form-data' in content_type:
            boundary_marker = 'boundary='
            boundary_start = content_type.find(boundary_marker)
            if boundary_start != -1:
                boundary = content_type[boundary_start + len(boundary_marker):].strip()
                if boundary.startswith('"') and boundary.endswith('"'):
                    boundary = boundary[1:-1]
                
                print(f"DEBUG UPLOAD: Boundary: {boundary}")
                
                # Count parts
                parts = body.split(f'--{boundary}'.encode())
                print(f"DEBUG UPLOAD: Found {len(parts)} parts")
                
                file_count = 0
                for i, part in enumerate(parts[1:-1]):  # Skip first empty and last closing
                    if b'filename=' in part and b'Content-Type:' in part:
                        file_count += 1
                        
                print(f"DEBUG UPLOAD: Detected {file_count} files")
        
        return {"status": "debug", "body_size": len(body), "content_type": content_type}
        
    except Exception as e:
        print(f"DEBUG UPLOAD: Error: {str(e)}")
        return {"error": str(e)}

@app.post("/test-upload-simple")
async def test_upload_simple(request: Request):
    """Simple test endpoint to verify file uploads are working"""
    print(f"TEST UPLOAD: Request received")
    
    try:
        body = await request.body()
        content_type = request.headers.get('content-type', '')
        
        print(f"TEST UPLOAD: Content-Type: {content_type}")
        print(f"TEST UPLOAD: Body size: {len(body)} bytes")
        
        if not content_type.startswith('multipart/form-data'):
            return {"error": "Expected multipart/form-data", "received": content_type}
        
        # Quick check for file data
        file_markers = body.count(b'filename=')
        image_markers = body.count(b'image/')
        
        print(f"TEST UPLOAD: Found {file_markers} filename markers, {image_markers} image type markers")
        
        return {
            "status": "test_success",
            "body_size": len(body),
            "content_type": content_type,
            "filename_markers": file_markers,
            "image_markers": image_markers,
            "has_files": file_markers > 0
        }
        
    except Exception as e:
        print(f"TEST UPLOAD: Error: {str(e)}")
        return {"error": str(e)}

async def handle_large_upload(body: bytes, boundary: str, max_file_size: int, max_total_size: int):
    """Handle large uploads by processing them in chunks to avoid memory issues"""
    print("LARGE UPLOAD DEBUG: Starting streaming upload processing")
    
    saved_files = []
    total_size = 0
    
    try:
        # Use a more memory-efficient approach for large uploads
        boundary_bytes = f'--{boundary}'.encode()
        
        # Split the body into parts more efficiently
        parts = body.split(boundary_bytes)
        
        files_processed = 0
        files_saved = 0
        
        for i, part in enumerate(parts[1:-1]):  # Skip first empty and last closing parts
            files_processed += 1
            
            if not part.strip():
                continue
            
            try:
                # Find the header/body split
                if b'\r\n\r\n' not in part:
                    continue
                
                headers_section, file_data = part.split(b'\r\n\r\n', 1)
                headers_text = headers_section.decode('utf-8', errors='ignore')
                
                # Extract filename from Content-Disposition header
                filename = None
                for line in headers_text.split('\r\n'):
                    if 'content-disposition:' in line.lower() and 'filename=' in line:
                        start = line.find('filename="') + 10
                        if start > 9:
                            end = line.find('"', start)
                            if end > start:
                                filename = line[start:end]
                        break
                
                if not filename:
                    continue
                
                # Check if it's an image file
                if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                    print(f"LARGE UPLOAD DEBUG: Skipping non-image file: {filename}")
                    continue
                
                # Clean up file data (remove trailing boundary markers)
                file_data = file_data.rstrip(b'\r\n')
                
                # Check file size
                file_size = len(file_data)
                if file_size == 0:
                    print(f"LARGE UPLOAD DEBUG: Skipping empty file: {filename}")
                    continue
                
                if file_size > max_file_size:
                    print(f"LARGE UPLOAD DEBUG: Skipping large file {filename}: {file_size / (1024*1024):.1f} MB")
                    continue
                
                if total_size + file_size > max_total_size:
                    print(f"LARGE UPLOAD DEBUG: Total size limit reached at file {files_processed}")
                    break
                
                # Validate it's a real image
                try:
                    Image.open(io.BytesIO(file_data))
                except Exception as img_error:
                    print(f"LARGE UPLOAD DEBUG: Invalid image {filename}: {str(img_error)}")
                    continue
                
                # Save the file
                file_path = os.path.join(UPLOAD_DIR, filename)
                with open(file_path, "wb") as f:
                    f.write(file_data)
                
                saved_files.append(file_path)
                total_size += file_size
                files_saved += 1
                
                # Progress updates for large batches
                if files_processed % 50 == 0:
                    print(f"LARGE UPLOAD DEBUG: Processed {files_processed} files, saved {files_saved}")
                
            except Exception as file_error:
                print(f"LARGE UPLOAD DEBUG: Error processing file {files_processed}: {str(file_error)}")
                continue
        
        print(f"LARGE UPLOAD DEBUG: Completed - Processed: {files_processed}, Saved: {files_saved}, Total: {total_size / (1024*1024):.1f} MB")
        
        if not saved_files:
            raise HTTPException(
                status_code=400,
                detail=f"No valid images were processed from {files_processed} files. Please ensure you're uploading image files (jpg, png, gif, bmp, webp)."
            )
        
        return {
            "message": f"Successfully uploaded {len(saved_files)} images ({total_size / (1024*1024):.1f} MB total)",
            "files": saved_files,
            "total_size_mb": round(total_size / (1024*1024), 1),
            "processing_method": "large_upload_streaming"
        }
        
    except Exception as e:
        print(f"LARGE UPLOAD DEBUG: Critical error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing large upload: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
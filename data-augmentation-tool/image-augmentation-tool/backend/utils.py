import os
import zipfile
import shutil

def clean_directory(dir_path: str):
    """Clean and recreate a directory"""
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
    os.makedirs(dir_path, exist_ok=True)

def create_zip(source_dir: str, max_file_size_mb: int = 100, max_files: int = None) -> str:
    """Create a zip file from all files in source directory"""
    zip_path = os.path.join(source_dir, "augmented_results.zip")
    max_file_size_bytes = max_file_size_mb * 1024 * 1024  # Convert MB to bytes
    
    # Remove existing zip if it exists
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            total_size = 0
            files_added = 0
            
            # Get all files first and sort them
            all_files = []
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file != "augmented_results.zip":  # Don't include the zip itself
                        file_path = os.path.join(root, file)
                        if os.path.exists(file_path):
                            all_files.append(file_path)
            
            # Sort files to ensure consistent ordering
            all_files.sort()
            
            # Limit the number of files to process (only if limit is set)
            if max_files is not None and len(all_files) > max_files:
                print(f"Warning: Found {len(all_files)} files, limiting to {max_files}")
                all_files = all_files[:max_files]
            
            print(f"Starting to create zip with {len(all_files)} files...")
            
            for i, file_path in enumerate(all_files):
                # Progress reporting for large datasets
                if i % 100 == 0 and i > 0:
                    print(f"Progress: {i}/{len(all_files)} files processed ({files_added} added)")
                
                # Check file size before adding
                try:
                    file_size = os.path.getsize(file_path)
                    
                    # Skip files that are too large individually
                    if file_size > max_file_size_bytes:
                        print(f"Skipping large file: {os.path.basename(file_path)} ({file_size / (1024*1024):.1f} MB)")
                        continue
                    
                    # Check if adding this file would exceed total size limit (now 5GB for large datasets)
                    max_total_size = max_file_size_bytes * 50  # 50x individual limit
                    if total_size + file_size > max_total_size:
                        print(f"Reached size limit, stopping at {files_added} files")
                        break
                    
                    # Check if we've reached the file count limit (only if limit is set)
                    if max_files is not None and files_added >= max_files:
                        print(f"Reached file count limit, stopping at {files_added} files")
                        break
                    
                    # Create relative path for archive
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    total_size += file_size
                    files_added += 1
                    
                except (OSError, IOError) as e:
                    print(f"Error processing file {os.path.basename(file_path)}: {e}")
                    continue
            
            print(f"Created zip with {files_added} files, total size: {total_size / (1024*1024):.1f} MB")
            
    except Exception as e:
        print(f"Error creating zip file: {e}")
        # If zip creation fails, try to create a simple zip with just a few files
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add only the first few image files
                image_files = [f for f in os.listdir(source_dir) 
                             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))]
                for i, file in enumerate(image_files[:10]):  # Limit to first 10 files
                    file_path = os.path.join(source_dir, file)
                    if os.path.getsize(file_path) < max_file_size_bytes:
                        zipf.write(file_path, file)
                        if i >= 9:  # Stop at 10 files
                            break
        except Exception as fallback_error:
            print(f"Fallback zip creation also failed: {fallback_error}")
            raise
    
    return zip_path
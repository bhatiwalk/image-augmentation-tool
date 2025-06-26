window.addEventListener('error', function(e) {
    console.error('Global error caught:', e.error);
    if (e.error && e.error.message && e.error.message.includes('Cannot read properties of null')) {
        console.error('Null reference error detected:', e.error.message);
        console.error('Error occurred at:', e.filename, 'line', e.lineno);
        return true;
    }
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    if (e.reason && e.reason.message && e.reason.message.includes('Cannot read properties of null')) {
        console.error('Null reference error in promise:', e.reason.message);
        e.preventDefault();
    }
});

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements with null checks
    const dropArea = document.getElementById('dropArea');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileInput');
    const inputPreview = document.getElementById('inputPreview');
    const outputPreview = document.getElementById('outputPreview');
    const processBtn = document.getElementById('processBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const statusIndicator = document.getElementById('statusIndicator');
    const dropdownBtn = document.getElementById('dropdownBtn');
    const transformDropdown = document.getElementById('transformDropdown');
    const imageCount = document.getElementById('imageCount');
    
    // Check for missing DOM elements
    const requiredElements = {
        dropArea, uploadBtn, fileInput, inputPreview, 
        outputPreview, processBtn, downloadBtn, statusIndicator, 
        dropdownBtn, transformDropdown, imageCount
    };
    
    for (const [name, element] of Object.entries(requiredElements)) {
        if (!element) {
            console.error(`Required DOM element not found: ${name}`);
            return; // Stop execution if critical elements are missing
        }
    }
    
    // Store uploaded files for processing
    let uploadedFiles = [];
    let isSelectingFolder = false; // Track current selection mode
    
    // Tool logout functionality
    const toolLogoutBtn = document.getElementById('toolLogoutBtn');
    if (toolLogoutBtn) {
        toolLogoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Confirm logout
            const confirmLogout = confirm('Are you sure you want to logout?');
            if (confirmLogout) {
                // Clear any stored user data
                localStorage.removeItem('userToken');
                localStorage.removeItem('userData');
                sessionStorage.clear();
                
                // Show logout message
                alert('You have been logged out successfully!');
                
                // Redirect to login page
                window.location.href = 'login.html';
            }
        });
    }

    // Toggle dropdown
    if (dropdownBtn && transformDropdown) {
        dropdownBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            transformDropdown.classList.toggle('active');
        });
    }
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function() {
        if (transformDropdown) {
            transformDropdown.classList.remove('active');
        }
    });
    
    // Handle file selection via button - show context menu for files or folder
    if (uploadBtn) {
        uploadBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showUploadMenu(e);
        });
    }
    
    // Show upload menu when button is clicked
    function showUploadMenu(e) {
        if (!uploadBtn) {
            console.error('uploadBtn not found');
            return;
        }
        
        // Create context menu
        const menu = document.createElement('div');
        menu.className = 'upload-menu';
        menu.innerHTML = `
            <div class="menu-item" data-type="files">
                <i class="fas fa-images"></i> Select Individual Images
            </div>
            <div class="menu-item" data-type="folder">
                <i class="fas fa-folder"></i> Select Entire Folder
            </div>
        `;
        
        // Position menu
        menu.style.cssText = `
            position: fixed;
            background: rgba(0, 0, 0, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 8px;
            padding: 10px;
            z-index: 1000;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
            min-width: 180px;
        `;
        
        // Add menu item styles
        const style = document.createElement('style');
        style.textContent = `
            .upload-menu .menu-item {
                padding: 10px 15px;
                cursor: pointer;
                border-radius: 5px;
                color: white;
                display: flex;
                align-items: center;
                gap: 10px;
                transition: background 0.2s;
            }
            .upload-menu .menu-item:hover {
                background: rgba(77, 171, 247, 0.3);
            }
        `;
        document.head.appendChild(style);
        
        const rect = uploadBtn.getBoundingClientRect();
        menu.style.left = rect.left + 'px';
        menu.style.top = (rect.bottom + 5) + 'px';
        
        document.body.appendChild(menu);
        
        // Handle menu clicks
        menu.addEventListener('click', function(e) {
            const menuItem = e.target.closest('.menu-item');
            if (menuItem) {
                const type = menuItem.dataset.type;
                console.log('Menu item clicked:', type);
                
                if (type === 'files') {
                    // Configure for individual files
                    isSelectingFolder = false;
                    fileInput.removeAttribute('webkitdirectory');
                    fileInput.removeAttribute('directory');
                    fileInput.setAttribute('multiple', '');
                    console.log('Configured for individual file selection');
                } else if (type === 'folder') {
                    // Configure for folder selection
                    isSelectingFolder = true;
                    fileInput.setAttribute('webkitdirectory', '');
                    fileInput.setAttribute('directory', '');
                    fileInput.removeAttribute('multiple');
                    console.log('Configured for folder selection');
                }
                
                // Trigger file input
                fileInput.value = '';
                fileInput.click();
            }
            menu.remove();
            document.head.removeChild(style);
        });
        
        // Remove menu when clicking outside
        setTimeout(() => {
            document.addEventListener('click', function removeMenu() {
                menu.remove();
                document.head.removeChild(style);
                document.removeEventListener('click', removeMenu);
            });
        }, 100);
    }
      // Handle file selection via input (both individual files and folders)
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const selectionType = isSelectingFolder ? 'folder' : 'individual';
            console.log(`File input changed (${selectionType}), files:`, this.files);
            console.log('Files array:', Array.from(this.files || []).map(f => ({ name: f.name, size: f.size, type: f.type })));
            
            if (this.files && this.files.length > 0) {
                console.log(`Processing ${selectionType} selection: ${this.files.length} files`);
                handleFiles(this.files, selectionType);
            } else {
                console.log('No files in input');
            }
        });
    }
    
    // Drag and drop handlers
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, function() {
                dropArea.classList.add('highlight');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, function() {
                dropArea.classList.remove('highlight');
            }, false);
        });
        
        dropArea.addEventListener('drop', function(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                console.log('Files dropped:', files.length);
                handleFiles(files, 'drag-drop');
            }
        });
    }
    
    // Handle the selected files
    function handleFiles(files, source = 'unknown') {
        console.log('handleFiles called with:', files.length, 'files from source:', source);
        console.log('Files array:', Array.from(files).map(f => ({ name: f.name, size: f.size, type: f.type })));
        
        const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
        const MAX_TOTAL_SIZE = 10 * 1024 * 1024 * 1024; // 10GB total
        // No file count limit - allow unlimited files
        
        // Filter only image files and check sizes
        const validFiles = [];
        let totalSize = 0;
        let rejectedFiles = [];
        
        Array.from(files).forEach(file => {
            const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'];
            const validExtensions = /\.(jpe?g|png|gif|bmp|webp)$/i;
            
            console.log(`Checking file: ${file.name}, type: ${file.type}, size: ${file.size} bytes`);
            
            if (!validTypes.includes(file.type) && !validExtensions.test(file.name)) {
                rejectedFiles.push(`${file.name}: Not an image file`);
                console.log(`Rejected ${file.name}: Not an image file`);
                return;
            }
            
            if (file.size > MAX_FILE_SIZE) {
                rejectedFiles.push(`${file.name}: Too large (${(file.size / (1024*1024)).toFixed(1)}MB, max 10MB)`);
                console.log(`Rejected ${file.name}: Too large`);
                return;
            }
            
            if (totalSize + file.size > MAX_TOTAL_SIZE) {
                rejectedFiles.push(`${file.name}: Would exceed total size limit`);
                console.log(`Rejected ${file.name}: Would exceed total size limit`);
                return;
            }
            
            validFiles.push(file);
            totalSize += file.size;
            console.log(`Accepted ${file.name}: ${file.size} bytes, running total: ${totalSize} bytes`);
        });
        
        console.log('Filtered to:', validFiles.length, 'valid files');
        console.log('Total size:', (totalSize / (1024*1024)).toFixed(1), 'MB');
        console.log('Total size in bytes:', totalSize);
        
        if (rejectedFiles.length > 0) {
            const maxShow = 3;
            const shown = rejectedFiles.slice(0, maxShow);
            const message = shown.join('\n') + (rejectedFiles.length > maxShow ? `\n...and ${rejectedFiles.length - maxShow} more` : '');
            showError('Some files were rejected:\n' + message);
        }
        
        if (validFiles.length === 0) {
            showError('No valid image files selected. Please select images under 10MB each (max 100MB total).');
            return;
        }
        
        // Store files for processing
        uploadedFiles = validFiles;
        console.log('Stored', uploadedFiles.length, 'files for processing');
        console.log('Sample stored files:', uploadedFiles.slice(0, 3).map(f => ({ name: f.name, size: f.size, type: f.type })));
        
        // Validate that uploadedFiles contains actual File objects
        const invalidFiles = uploadedFiles.filter(f => !(f instanceof File));
        if (invalidFiles.length > 0) {
            console.error('Found invalid file objects:', invalidFiles);
        }
        
        // Clear previous input
        if (inputPreview) {
            inputPreview.innerHTML = '';
        }
        
        // Update image count with size info - ensure totalSize is passed correctly
        console.log('Calling updateImageCount with:', validFiles.length, 'files and', totalSize, 'bytes total size');
        updateImageCount(validFiles.length, totalSize);
        
        // For large numbers of files, limit preview display
        const MAX_PREVIEW_FILES = 500;
        const filesToDisplay = validFiles.slice(0, MAX_PREVIEW_FILES);
        
        if (validFiles.length > MAX_PREVIEW_FILES) {
            const infoDiv = document.createElement('div');
            infoDiv.className = 'preview-info';
            infoDiv.innerHTML = `<i class="fas fa-info-circle"></i> Showing first ${MAX_PREVIEW_FILES} of ${validFiles.length} files for performance`;
            if (inputPreview) {
                inputPreview.appendChild(infoDiv);
            }
        }
        
        // Display images (limited for performance)
        let loadedCount = 0;
        
        filesToDisplay.forEach((file, index) => {
            console.log(`Processing file ${index + 1}:`, file.name, file.type, file.size);
            const reader = new FileReader();
            
            reader.onload = function(e) {
                console.log(`File ${index + 1} loaded successfully:`, file.name);
                loadedCount++;
                
                try {
                    createImagePreview(e.target.result, file.name, inputPreview);
                } catch (error) {
                    console.error(`Error creating preview for ${file.name}:`, error);
                }
                
                if (loadedCount === filesToDisplay.length) {
                    console.log('All preview files loaded, removing placeholder');
                    // Remove placeholder after last image loads
                    if (inputPreview) {
                        const placeholder = inputPreview.querySelector('.placeholder');
                        if (placeholder) placeholder.remove();
                    }
                    
                    // Enable process button
                    if (processBtn) {
                        processBtn.disabled = false;
                    }
                    console.log('Process button enabled');
                }
            };
            
            reader.onerror = function(error) {
                console.error('Error reading file:', file.name, error);
                loadedCount++;
                
                if (loadedCount === filesToDisplay.length) {
                    if (inputPreview) {
                        const placeholder = inputPreview.querySelector('.placeholder');
                        if (placeholder) placeholder.remove();
                    }
                    if (processBtn) {
                        processBtn.disabled = false;
                    }
                }
            };
            
            try {
                reader.readAsDataURL(file);
            } catch (error) {
                console.error(`Error starting file read for ${file.name}:`, error);
                loadedCount++;
            }
        });
        
        // Reset output
        resetOutputPreview();
    }
    
    function updateImageCount(count, totalSize = null) {
        if (!imageCount) {
            console.warn('imageCount element not found');
            return;
        }
        
        let text = `(${count} image${count !== 1 ? 's' : ''})`;
        if (totalSize !== null && totalSize > 0) {
            const sizeInMB = totalSize / (1024 * 1024);
            if (sizeInMB < 0.1) {
                text += ` - ${(totalSize / 1024).toFixed(1)}KB`;
            } else {
                text += ` - ${sizeInMB.toFixed(1)}MB`;
            }
        }
        imageCount.textContent = text;
        console.log('Updated image count:', text, 'Total size bytes:', totalSize);
    }
    
    function createImagePreview(src, alt, container) {
        console.log('createImagePreview called:', alt, container ? 'container provided' : 'no container');
        
        const imgContainer = document.createElement('div');
        imgContainer.className = 'image-item';
        
        const img = document.createElement('img');
        img.src = src;
        img.alt = alt;
        img.loading = 'lazy';
        
        // Add load handler for debugging
        img.onload = function() {
            console.log('Image preview loaded successfully:', alt);
        };
        
        img.onerror = function() {
            console.error('Error loading image preview:', alt);
        };
        
        const tooltip = document.createElement('div');
        tooltip.className = 'image-tooltip';
        tooltip.textContent = alt;
        
        imgContainer.appendChild(img);
        imgContainer.appendChild(tooltip);
        
        if (container) {
            container.appendChild(imgContainer);
            console.log('Image preview added to container:', alt);
        } else {
            console.error('No container provided for image preview:', alt);
        }
    }
    
    function resetOutputPreview() {
        if (outputPreview) {
            outputPreview.innerHTML = '<div class="placeholder">Augmented images will appear here after processing</div>';
        }
        if (downloadBtn) {
            downloadBtn.disabled = true;
        }
        if (processBtn) {
            processBtn.disabled = uploadedFiles.length === 0;
        }
    }
    
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        
        // Handle multi-line messages
        if (message.includes('\n')) {
            errorDiv.innerHTML = message.split('\n').map(line => `<div>${line}</div>`).join('');
        } else {
            errorDiv.textContent = message;
        }
        
        // Remove any existing error
        const existingError = document.querySelector('.error-message');
        if (existingError) existingError.remove();
        
        document.body.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 6000); // Longer timeout for multi-line messages
    }
      // Process the images
    if (processBtn) {
        processBtn.addEventListener('click', async function() {
            console.log('Process button clicked, uploadedFiles:', uploadedFiles.length);
            console.log('Sample uploadedFiles:', uploadedFiles.slice(0, 3).map(f => ({ name: f.name, size: f.size, type: f.type })));
            
            if (uploadedFiles.length === 0) {
                showError('Please select images first');
                return;
            }
            
            // Validate that we have actual File objects
            const validFileObjects = uploadedFiles.filter(f => f instanceof File && f.name && f.size > 0);
            console.log(`Valid file objects: ${validFileObjects.length} out of ${uploadedFiles.length}`);
            
            if (validFileObjects.length === 0) {
                showError('No valid file objects found. Please re-select your images.');
                return;
            }
            
            if (validFileObjects.length !== uploadedFiles.length) {
                console.warn(`Some invalid file objects detected. Using ${validFileObjects.length} valid files.`);
                uploadedFiles = validFileObjects; // Update to only valid files
            }

            const augmentations = getSelectedAugmentations();
            if (augmentations.length === 0) {
                showError('Please select at least one augmentation type');
                return;
            }

            // No file count limits - proceed directly to processing
            await processImages(augmentations);
        });
    }
    
    function getSelectedAugmentations() {
        return Array.from(document.querySelectorAll('.dropdown-content input[type="checkbox"]:checked'))
                   .map(checkbox => checkbox.id);
    }
    
    async function processImages(augmentations) {
        if (statusIndicator) {
            statusIndicator.style.display = 'flex';
        }
        if (downloadBtn) {
            downloadBtn.disabled = true;
        }
        if (outputPreview) {
            outputPreview.innerHTML = '<div class="placeholder">Processing images...</div>';
        }
        if (processBtn) {
            processBtn.disabled = true;
        }

        // Show estimated processing time for large datasets
        const estimatedFiles = uploadedFiles.length * (augmentations.length + 1);
        if (estimatedFiles > 5000 && statusIndicator) {
            const statusText = statusIndicator.querySelector('div');
            if (statusText) {
                statusText.textContent = `Processing ${estimatedFiles} images... This may take several minutes.`;
            }
        }

        try {
            // Handle large uploads (>1000 files) with batching, use standard for smaller uploads
            if (uploadedFiles.length > 1000) {
                console.log('Large upload detected (>1000 files), using batch upload approach');
                await uploadFilesBatch(uploadedFiles);
            } else {
                console.log(`Normal upload size (${uploadedFiles.length} files), using standard approach`);
                await uploadFilesStandard(uploadedFiles);
            }

            // 2. Request augmentations
            console.log('Requesting augmentations...');
            const augmentResponse = await fetch('http://localhost:8000/augment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    augmentations: augmentations.map(aug => {
                        // Map frontend IDs to backend IDs
                        const mapping = {
                            flipHorizontal: 'flip_horizontal',
                            flipVertical: 'flip_vertical',
                            rotate90: 'rotate_90',
                            rotate180: 'rotate_180',
                            rotate270: 'rotate_270',
                            brightness: 'brightness',
                            contrast: 'contrast',
                            blur: 'blur',
                            noise: 'noise',
                            crop: 'crop'
                        };
                        return mapping[aug] || aug;
                    })
                })
            });

            if (!augmentResponse.ok) {
                let error;
                try {
                    error = await augmentResponse.json();
                } catch (parseError) {
                    console.warn('Could not parse augmentation error response:', parseError);
                    error = {};
                }
                throw new Error((error && error.detail) || 'Augmentation failed');
            }

            const augmentResult = await augmentResponse.json();
            console.log('Augmentation successful:', augmentResult);

            // 3. Wait a moment for files to be written, then display results
            setTimeout(async () => {
                await displayAugmentedResults();
            }, 1000);

            if (downloadBtn) {
                downloadBtn.disabled = false;
            }
            
            // Safe access to augmentResult.message
            const resultMessage = (augmentResult && augmentResult.message) 
                ? augmentResult.message 
                : 'augmentations completed successfully';
            showSuccess(`Successfully generated ${resultMessage}`);

        } catch (error) {
            let errorMessage = 'An error occurred during processing';
            
            // Safe access to error.message
            if (error && error.message) {
                const msg = error.message;
                errorMessage = msg;
                
                // Handle specific error types
                if (msg.includes('Files are too large')) {
                    errorMessage = 'Files are too large. Please reduce the number of images or use smaller images (max 10MB per file, 10GB total).';
                } else if (msg.includes('maximum file size')) {
                    errorMessage = 'File size limit exceeded. Please use smaller images.';
                } else if (msg.includes('413')) {
                    errorMessage = 'Upload size too large. Please select smaller batches of images (try 500-800 at a time).';
                } else if (msg.includes('Failed to fetch')) {
                    errorMessage = 'Cannot connect to server. Please ensure the backend server is running on http://localhost:8000';
                } else if (msg.includes('No valid images were uploaded')) {
                    errorMessage = 'No valid images were uploaded. This may happen with very large folders. Try uploading in smaller batches or check that the files are valid image formats (jpg, png, gif, bmp, webp).';
                }
            }
            
            showError('Error: ' + errorMessage);
            console.error('Processing error:', error);
        } finally {
            if (statusIndicator) {
                statusIndicator.style.display = 'none';
            }
            if (processBtn) {
                processBtn.disabled = false;
            }
        }
    }
    
    async function displayAugmentedResults() {
        try {
            console.log('Fetching augmented images list...');
            
            // First, test what's in the directory
            try {
                const testResponse = await fetch('http://localhost:8000/test-images');
                if (testResponse.ok) {
                    const testResult = await testResponse.json();
                    console.log('Directory test:', testResult);
                } else {
                    console.log('Test endpoint failed:', testResponse.status, testResponse.statusText);
                }
            } catch (testError) {
                console.log('Test endpoint error:', testError ? testError.message : 'Unknown test error');
            }
            
            // Get the list of augmented images
            const response = await fetch('http://localhost:8000/augmented-images');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('Augmented images response:', result);
            
            // Clear output preview
            if (outputPreview) {
                outputPreview.innerHTML = '';
            }
            
            if (result.images && result.images.length > 0) {
                console.log(`Found ${result.images.length} images to display`);
                
                // Display each augmented image
                result.images.forEach((imageInfo, index) => {
                    if (!imageInfo || !imageInfo.filename) {
                        console.warn(`Skipping invalid image info at index ${index}:`, imageInfo);
                        return;
                    }
                    
                    const imgContainer = document.createElement('div');
                    imgContainer.className = 'image-item';
                    
                    const img = document.createElement('img');
                    // Use the correct URL for serving static files
                    const imageUrl = `http://localhost:8000/augmented/${imageInfo.filename}`;
                    img.src = imageUrl;
                    img.alt = imageInfo.description || imageInfo.filename;
                    img.loading = 'lazy';
                    
                    console.log(`Loading image ${index + 1}: ${imageUrl}`);
                    
                    // Add load success handler
                    img.onload = function() {
                        console.log(`Successfully loaded: ${imageInfo.filename}`);
                    };
                    
                    // Add error handling for image loading
                    img.onerror = function() {
                        console.error('Failed to load image:', imageInfo.filename, 'URL:', imageUrl);
                        // Show error placeholder
                        this.style.display = 'none';
                        this.alt = `Error loading: ${imageInfo.filename}`;
                    };
                    
                    const tooltip = document.createElement('div');
                    tooltip.className = 'image-tooltip';
                    tooltip.textContent = imageInfo.description || imageInfo.filename || 'Image';
                    
                    imgContainer.appendChild(img);
                    imgContainer.appendChild(tooltip);
                    if (outputPreview) {
                        outputPreview.appendChild(imgContainer);
                    }
                });
                
                console.log(`Displayed ${result.images.length} augmented images`);
            } else {
                console.log('No images found in response');
                if (outputPreview) {
                    outputPreview.innerHTML = '<div class="placeholder">No augmented images found</div>';
                }
            }
            
        } catch (error) {
            console.error('Error displaying results:', error);
            if (outputPreview) {
                outputPreview.innerHTML = '<div class="placeholder">Error loading augmented images</div>';
            }
            const errorMessage = (error && error.message) ? error.message : 'Unknown error';
            showError('Error displaying augmented images: ' + errorMessage);
        }
    }
    
    function showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.textContent = message;
        successDiv.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #28a745;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            z-index: 1000;
            animation: fadeIn 0.3s;
        `;
        
        // Remove any existing success message
        const existingSuccess = document.querySelector('.success-message');
        if (existingSuccess) existingSuccess.remove();
        
        document.body.appendChild(successDiv);
        setTimeout(() => successDiv.remove(), 4000);
    }
    
    // Download processed images
    if (downloadBtn) {
        downloadBtn.addEventListener('click', async function() {
            try {
                console.log('Starting download...');
                downloadBtn.disabled = true;
                downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Downloading...';
                
                const response = await fetch('http://localhost:8000/download');
                if (!response.ok) {
                    let error;
                    try {
                        error = await response.json();
                    } catch (parseError) {
                        console.warn('Could not parse download error response:', parseError);
                        error = {};
                    }
                    throw new Error((error && error.detail) || 'Download failed');
                }
                
                // Get the blob and create download
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'augmented_dataset.zip';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
                
                showSuccess('Download completed successfully!');
                
            } catch (error) {
                const errorMessage = (error && error.message) ? error.message : 'Unknown download error';
                showError('Download failed: ' + errorMessage);
                console.error('Download error:', error);
            } finally {
                if (downloadBtn) {
                    downloadBtn.disabled = false;
                    downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download All';
                }
            }
        });
    }
    
    async function uploadFilesStandard(files) {
        console.log('uploadFilesStandard called with', files.length, 'files');
        
        if (!files || files.length === 0) {
            throw new Error('No files provided to uploadFilesStandard');
        }
        
        // Test upload connection first
        const testResult = await testUploadConnection(files.slice(0, 1)); // Test with first file
        if (!testResult) {
            throw new Error('Upload connection test failed - files may not be reaching the server');
        }
        
        const formData = new FormData();
        let addedFiles = 0;
        
        files.forEach((file, index) => {
            if (file && file.name && file.size > 0) {
                console.log(`Adding file ${index + 1} to FormData: ${file.name} (${file.size} bytes)`);
                formData.append('files', file);
                addedFiles++;
            } else {
                console.warn(`Skipping invalid file at index ${index}:`, file);
            }
        });
        
        console.log(`Added ${addedFiles} files to FormData out of ${files.length} provided`);
        
        if (addedFiles === 0) {
            throw new Error('No valid files were added to the upload');
        }

        console.log('Uploading files to /upload endpoint...');
        const uploadResponse = await fetch('http://localhost:8000/upload', {
            method: 'POST',
            body: formData
        });

        console.log('Upload response status:', uploadResponse.status, uploadResponse.statusText);

        if (!uploadResponse.ok) {
            let error;
            try {
                error = await uploadResponse.json();
                console.log('Upload error response:', error);
            } catch (parseError) {
                console.warn('Could not parse upload error response:', parseError);
                error = {};
            }
            throw new Error((error && error.detail) || 'Upload failed');
        }

        const uploadResult = await uploadResponse.json();
        console.log('Upload successful:', uploadResult);
        return uploadResult;
    }
    
    async function uploadFilesBatch(files) {
        console.log('uploadFilesBatch called with', files.length, 'files');
        const batchSize = 500; // Upload in batches of 500 files
        const totalBatches = Math.ceil(files.length / batchSize);
        
        console.log(`Uploading ${files.length} files in ${totalBatches} batches of ${batchSize} each`);
        
        for (let i = 0; i < totalBatches; i++) {
            const start = i * batchSize;
            const end = Math.min(start + batchSize, files.length);
            const batchFiles = files.slice(start, end);
            
            console.log(`Uploading batch ${i + 1}/${totalBatches}: files ${start + 1}-${end}`);
            console.log('Batch files:', batchFiles.map(f => ({ name: f.name, size: f.size })));
            
            // Update status indicator
            if (statusIndicator) {
                const statusText = statusIndicator.querySelector('div');
                if (statusText) {
                    statusText.textContent = `Uploading batch ${i + 1}/${totalBatches} (${batchFiles.length} files)...`;
                }
            }
            
            const formData = new FormData();
            batchFiles.forEach((file, index) => {
                console.log(`Adding batch file ${index + 1}: ${file.name}`);
                formData.append('files', file);
            });
            
            // Add batch information
            formData.append('batch_number', (i + 1).toString());
            formData.append('is_first_batch', (i === 0).toString());
            
            console.log(`Sending batch ${i + 1} to /upload-batch endpoint...`);
            const uploadResponse = await fetch('http://localhost:8000/upload-batch', {
                method: 'POST',
                body: formData
            });

            console.log(`Batch ${i + 1} response status:`, uploadResponse.status, uploadResponse.statusText);

            if (!uploadResponse.ok) {
                let error;
                try {
                    error = await uploadResponse.json();
                    console.log(`Batch ${i + 1} error response:`, error);
                } catch (parseError) {
                    console.warn('Could not parse batch upload error response:', parseError);
                    error = {};
                }
                throw new Error((error && error.detail) || `Batch ${i + 1} upload failed`);
            }

            const uploadResult = await uploadResponse.json();
            console.log(`Batch ${i + 1} upload successful:`, uploadResult);
            
            // Small delay between batches to avoid overwhelming the server
            if (i < totalBatches - 1) {
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        }
        
        console.log('All batches uploaded successfully');
    }
    
    // Test function to verify uploads work
    async function testUploadConnection(files) {
        console.log('Testing upload connection with', files.length, 'files');
        
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));
        
        try {
            const response = await fetch('http://localhost:8000/test-upload-simple', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            console.log('Upload test result:', result);
            
            if (result.has_files) {
                console.log('✅ Files are being sent correctly to backend');
                return true;
            } else {
                console.log('❌ No files detected in backend');
                return false;
            }
        } catch (error) {
            console.error('Upload test failed:', error);
            return false;
        }
    }
});

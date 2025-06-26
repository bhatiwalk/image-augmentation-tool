import numpy as np
from skimage import transform, util, color, filters
import random
import os
from PIL import Image
from typing import List

AUGMENTED_DIR = "augmented"

def apply_flip(img: np.ndarray, direction: str) -> np.ndarray:
    if direction == "horizontal":
        return np.fliplr(img)
    elif direction == "vertical":
        return np.flipud(img)
    elif direction == "both":
        return np.flipud(np.fliplr(img))
    return img

def apply_rotate(img: np.ndarray, angle: int) -> np.ndarray:
    # Handle different image shapes (grayscale vs RGB)
    if len(img.shape) == 3:
        rotated = transform.rotate(img, angle=angle, mode='edge', preserve_range=True)
    else:
        rotated = transform.rotate(img, angle=angle, mode='edge', preserve_range=True)
    return rotated.astype(np.uint8)

def apply_zoom(img: np.ndarray, scale: float) -> np.ndarray:
    height, width = img.shape[:2]
    # Use skimage's rescale properly
    if len(img.shape) == 3:
        scaled = transform.rescale(img, scale=scale, anti_aliasing=True, channel_axis=2, preserve_range=True)
    else:
        scaled = transform.rescale(img, scale=scale, anti_aliasing=True, preserve_range=True)
    scaled = scaled.astype(np.uint8)
    
    # Random crop to original size if scaled image is larger
    s_h, s_w = scaled.shape[:2]
    if s_h >= height and s_w >= width:
        crop_y = random.randint(0, s_h - height)
        crop_x = random.randint(0, s_w - width)
        return scaled[crop_y:crop_y+height, crop_x:crop_x+width]
    else:
        # If scaled image is smaller, pad it
        return scaled

def apply_noise(img: np.ndarray, noise_type: str = "gaussian") -> np.ndarray:
    # Normalize to 0-1 range for skimage
    img_normalized = img.astype(np.float64) / 255.0
    noisy = util.random_noise(img_normalized, mode=noise_type)
    return (noisy * 255).astype(np.uint8)

def apply_brightness(img: np.ndarray, factor: float = 1.2) -> np.ndarray:
    # Convert to float to avoid overflow
    img_float = img.astype(np.float64)
    brightened = img_float * factor
    return np.clip(brightened, 0, 255).astype(np.uint8)

def apply_contrast(img: np.ndarray, factor: float = 1.5) -> np.ndarray:
    # Convert to float and apply contrast
    img_float = img.astype(np.float64)
    mean = np.mean(img_float)
    contrasted = (img_float - mean) * factor + mean
    return np.clip(contrasted, 0, 255).astype(np.uint8)

def apply_blur(img: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    if len(img.shape) == 3:
        blurred = filters.gaussian(img, sigma=sigma, channel_axis=2, preserve_range=True)
    else:
        blurred = filters.gaussian(img, sigma=sigma, preserve_range=True)
    return blurred.astype(np.uint8)

def apply_crop(img: np.ndarray, crop_size: float = 0.8) -> np.ndarray:
    h, w = img.shape[:2]
    new_h, new_w = int(h * crop_size), int(w * crop_size)
    
    # Ensure we don't crop to zero size
    new_h = max(new_h, 1)
    new_w = max(new_w, 1)
    
    y = random.randint(0, max(0, h - new_h))
    x = random.randint(0, max(0, w - new_w))
    return img[y:y+new_h, x:x+new_w]

def apply_augmentations(input_files: List[str], augmentations: List[str], output_dir: str = "augmented", max_output_files: int = None) -> List[str]:
    output_files = []
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Update the global AUGMENTED_DIR to use the passed output directory
    global AUGMENTED_DIR
    AUGMENTED_DIR = output_dir
    
    # No file count limits when max_output_files is None
    if max_output_files is not None:
        # Calculate estimated output count
        estimated_output = len(input_files) * (len(augmentations) + 1)  # +1 for original
        if estimated_output > max_output_files:
            print(f"Warning: Estimated output ({estimated_output}) exceeds limit ({max_output_files})")
            # Reduce augmentations or input files to stay within limit
            max_augs_per_image = max(1, (max_output_files // len(input_files)) - 1)
            if max_augs_per_image < len(augmentations):
                augmentations = augmentations[:max_augs_per_image]
                print(f"Limiting to {max_augs_per_image} augmentations per image")
    
    for i, file_path in enumerate(input_files):
        try:
            # Load image
            pil_img = Image.open(file_path)
            # Convert to RGB if necessary
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            
            img = np.array(pil_img)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Save original first
            output_path = os.path.join(AUGMENTED_DIR, f"{base_name}_original.jpg")
            Image.fromarray(img).save(output_path, quality=95)
            output_files.append(output_path)
            
            # Apply selected augmentations
            for aug in augmentations:
                try:
                    augmented = None
                    
                    if aug == "flip_horizontal":
                        augmented = apply_flip(img, "horizontal")
                        suffix = "flip_horizontal"
                        
                    elif aug == "flip_vertical":
                        augmented = apply_flip(img, "vertical")
                        suffix = "flip_vertical"
                        
                    elif aug == "rotate_90":
                        augmented = apply_rotate(img, 90)
                        suffix = "rotate_90"
                        
                    elif aug == "rotate_180":
                        augmented = apply_rotate(img, 180)
                        suffix = "rotate_180"
                        
                    elif aug == "rotate_270":
                        augmented = apply_rotate(img, 270)
                        suffix = "rotate_270"
                        
                    elif aug == "brightness":
                        augmented = apply_brightness(img, factor=random.uniform(1.1, 1.5))
                        suffix = "brightness"
                        
                    elif aug == "contrast":
                        augmented = apply_contrast(img, factor=random.uniform(1.2, 1.8))
                        suffix = "contrast"
                        
                    elif aug == "blur":
                        augmented = apply_blur(img, sigma=random.uniform(0.5, 2.0))
                        suffix = "blur"
                        
                    elif aug == "noise":
                        augmented = apply_noise(img, "gaussian")
                        suffix = "noise"
                        
                    elif aug == "crop":
                        augmented = apply_crop(img, crop_size=random.uniform(0.7, 0.9))
                        suffix = "crop"
                    
                    if augmented is not None:
                        output_path = os.path.join(AUGMENTED_DIR, f"{base_name}_{suffix}.jpg")
                        Image.fromarray(augmented).save(output_path, quality=95)
                        output_files.append(output_path)
                        
                        # Check if we're approaching the file limit (only if limit is set)
                        if max_output_files is not None and len(output_files) >= max_output_files:
                            print(f"Reached maximum output files limit ({max_output_files}), stopping")
                            return output_files
                        
                except Exception as e:
                    print(f"Error applying {aug} to {base_name}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
            continue
            
    return output_files
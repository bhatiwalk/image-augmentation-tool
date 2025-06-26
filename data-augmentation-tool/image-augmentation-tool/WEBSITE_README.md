# DataAug Pro - Complete Website

This is a complete website for the Data Augmentation Tool with multiple pages and navigation.

## Website Structure

### Pages

1. **home.html** - Main landing page
   - Professional landing page with features overview
   - Call-to-action buttons
   - Navigation to all other pages
   - Login/Signup links in profile dropdown

2. **index.html** - Data Augmentation Tool
   - The main functional tool for image augmentation
   - Upload images/folders
   - Select augmentation types
   - Preview and download results
   - Navigation back to home page

3. **login.html** - User Login Page
   - Login form with email/password
   - Social login options
   - Redirects to home page after login

4. **signup.html** - User Registration Page
   - Registration form with validation
   - Password strength checker
   - Terms and conditions
   - Redirects to home page after signup

## Navigation Flow

```
home.html (Landing Page)
├── Tool → index.html (Main Tool)
├── Login → login.html → home.html
├── Sign Up → signup.html → home.html
└── Features/Contact (Same page sections)

index.html (Tool)
└── Back to Home → home.html
```

## Key Features

### Landing Page (home.html)
- Modern, professional design
- Animated background particles
- Responsive navigation bar
- Feature showcase with icons
- Statistics section
- Social links in footer

### Main Tool (index.html)
- Drag & drop file upload
- File and folder selection dialog
- Multiple augmentation types (10+)
- Live preview of results
- Batch processing support
- ZIP download functionality

### Authentication Pages
- Consistent design theme
- Form validation
- Error handling
- Smooth animations
- Mobile responsive

## Usage

1. **Start at home.html** - This is your main landing page
2. **Click "Try It Now"** - Goes to the main tool (index.html)
3. **Use the tool** - Upload images and generate augmentations
4. **Navigate back** - Use "Back to Home" to return to landing page

## File Dependencies

- **FontAwesome 6.4.0** - Icons (loaded from CDN)
- **style.css** - Styles for the main tool
- **script.js** - JavaScript for the tool functionality

## Backend Integration

The tool connects to a Python backend server running on `http://localhost:8000` with these endpoints:
- `/upload` - Upload images
- `/upload-batch` - Batch upload for large datasets
- `/augment` - Process augmentations
- `/augmented-images` - Get result list
- `/augmented/{filename}` - Serve result images
- `/download` - Download ZIP file

## Responsive Design

All pages are fully responsive and work on:
- Desktop computers
- Tablets
- Mobile phones

## Browser Support

- Chrome (recommended)
- Firefox
- Safari
- Edge

Modern browser features used:
- CSS Grid/Flexbox
- Backdrop filter
- File API
- Fetch API
- ES6+ JavaScript

# Learn & Earn - React Website

A React-based login page for the Learn & Earn platform.

## Setup Instructions

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```

3. **Build for production:**
   ```bash
   npm run build
   ```

4. **Preview production build:**
   ```bash
   npm run preview
   ```

## Technologies Used

- React 18
- Vite (build tool)
- Tailwind CSS (styling)

## Project Structure

```
.
├── index.html          # HTML entry point
├── package.json        # Dependencies and scripts
├── vite.config.js     # Vite configuration
├── tailwind.config.js # Tailwind CSS configuration
├── postcss.config.js  # PostCSS configuration
└── src/
    ├── main.jsx       # React entry point
    ├── App.jsx        # Main component
    └── index.css      # Global styles with Tailwind directives
```

## Notes

- The component uses Tailwind CSS for styling
- Images are loaded from Google Cloud Storage URLs
- The layout is designed for a 1440px width viewport


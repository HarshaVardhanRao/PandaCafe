# PandaCafe POS Frontend

React + TypeScript + Vite + TailwindCSS

## Development

```bash
npm install
npm run dev
```

Visit http://localhost:3000

## Build

```bash
npm run build
```

## Project Structure

```
src/
├── api/          # API client
├── components/   # Reusable components
├── layouts/      # Page layouts
├── pages/        # Page components
├── store/        # Zustand state management
├── styles/       # Global styles
├── types/        # TypeScript types
├── utils/        # Utility functions
└── App.tsx       # Main app component
```

## Architecture

- **State Management**: Zustand for lightweight state
- **API Client**: Axios with interceptors
- **Routing**: React Router v6
- **Styling**: TailwindCSS
- **Build Tool**: Vite

## Key Features

- User authentication
- Product browsing
- Order creation and management
- Billing interface
- Payment processing
- Inventory lookup

## Environment Variables

Create `.env` file:

```
VITE_API_URL=http://localhost:8000/api/v1
VITE_APP_NAME=PandaCafe POS
```

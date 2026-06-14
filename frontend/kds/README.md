# PandaCafe KDS Frontend

React + TypeScript + Vite + TailwindCSS + WebSockets

## Development

```bash
npm install
npm run dev
```

Visit http://localhost:3001

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

- **State Management**: Zustand for order and KDS state
- **Real-time Updates**: WebSocket for live order updates
- **API Client**: Axios for REST API
- **Routing**: React Router v6
- **Styling**: TailwindCSS

## Key Features

- Real-time order display
- Order status updates (Pending, Preparing, Ready)
- Timer for preparation time
- Print KOT
- Accept/Start/Complete orders
- Low stock alerts
- Notifications

## WebSocket Connection

KDS maintains WebSocket connection to backend for:
- Live order updates
- Status changes
- Notifications
- Printer alerts

## Environment Variables

Create `.env` file:

```
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/api/v1
VITE_APP_NAME=PandaCafe KDS
```

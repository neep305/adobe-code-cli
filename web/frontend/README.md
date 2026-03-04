# Adobe AEP Web UI - Frontend

Next.js 14 frontend for the Adobe Experience Platform Web UI.

## Features

- **Authentication**: JWT-based login and registration
- **Batch Monitoring**: Real-time batch status with WebSocket updates
- **Modern UI**: Built with shadcn/ui and Tailwind CSS
- **Type-Safe**: Full TypeScript support
- **State Management**: React Query for server state

## Development

### Prerequisites

- Node.js 20+
- npm or yarn

### Setup

1. Install dependencies:
```bash
npm install
```

2. Copy environment variables:
```bash
cp .env.local.example .env.local
```

3. Update `.env.local` with your backend URL:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

4. Run the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

## Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── login/             # Login page
│   ├── register/          # Registration page
│   ├── batches/           # Batch monitoring pages
│   ├── dataflows/         # Dataflow monitoring (planned)
│   ├── datasets/          # Dataset management (planned)
│   └── schemas/           # Schema management (planned)
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── batch/            # Batch-specific components
│   ├── dashboard-layout.tsx
│   └── protected-route.tsx
├── hooks/                # Custom React hooks
│   ├── useBatch.ts       # Batch API hooks (React Query)
│   └── useBatchWebSocket.ts
├── lib/                  # Utilities and configurations
│   ├── api.ts           # API client
│   ├── auth.tsx         # Authentication context
│   ├── utils.ts         # Utility functions
│   └── types/           # TypeScript types
└── public/              # Static assets
```

## Key Technologies

- **Next.js 14**: App Router with Server Components
- **React 18**: UI framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **shadcn/ui**: Component library
- **React Query**: Server state management
- **WebSocket**: Real-time updates
- **date-fns**: Date formatting

## Features Implemented

### ✅ Phase 1: Foundation & Authentication
- [x] Next.js 14 project setup
- [x] Tailwind CSS + shadcn/ui configuration
- [x] API client with JWT handling
- [x] Authentication pages (login/register)
- [x] Protected route wrapper
- [x] Dashboard layout with navigation

### ✅ Slice 1: Batch Status Monitor
- [x] Batch list page
- [x] Batch detail page with real-time updates
- [x] WebSocket integration for live status
- [x] Batch status badge component
- [x] Progress bar component
- [x] Metrics card component
- [x] Automatic polling fallback

## Backend Integration

The frontend connects to the FastAPI backend at `http://localhost:8000`. Ensure the backend is running before starting the frontend.

### API Endpoints Used

- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Get current user
- `GET /api/batches` - List batches
- `GET /api/batches/{id}` - Get batch details
- `WS /ws/batch/{id}/status` - Real-time batch updates

## WebSocket Connection

The batch detail page establishes a WebSocket connection for real-time updates:

```typescript
// Connects with JWT token
ws://localhost:8000/ws/batch/{batch_id}/status?token={jwt}

// Message types:
// - "connected": Initial connection confirmation
// - "status_update": Batch status changed
// - "ping"/"pong": Heartbeat messages
```

## Docker Deployment

The frontend can be run in Docker using the provided Dockerfile:

```bash
# Development (with hot reload)
docker-compose up frontend

# Production build
FRONTEND_TARGET=runner docker-compose up frontend
```

## Next Steps

### Planned Features

1. **Slice 2: Dataflow Health Dashboard**
   - List dataflows with health indicators
   - Dataflow detail page with run history
   - Health analysis with charts (Recharts)
   - Error aggregation table

2. **Slice 3: Schema Management**
   - Schema list and detail pages
   - Schema browser with field tree view
   - XDM field group display

3. **Slice 4: AI Schema Generation**
   - File upload wizard
   - AI-powered schema analysis
   - Schema preview and editing
   - Create schema in Adobe AEP

4. **Slice 5: Dataset Management**
   - Dataset list and creation
   - Enable/disable profile and identity
   - Link to batches for dataset

### Enhancements
- [ ] Dark mode support
- [ ] User preferences
- [ ] Notifications system
- [ ] Advanced filtering and search
- [ ] Bulk operations
- [ ] Export data functionality

## Troubleshooting

### WebSocket Connection Issues

If WebSocket connections fail:
1. Check backend is running and accessible
2. Verify JWT token is valid
3. Check browser console for WebSocket errors
4. Fallback to polling will activate automatically

### CORS Issues

If seeing CORS errors:
1. Ensure backend CORS is configured for `http://localhost:3000`
2. Check `NEXT_PUBLIC_API_URL` in `.env.local`
3. Restart both frontend and backend

### Authentication Issues

If login fails:
1. Check backend `/api/auth/login` endpoint is working
2. Verify credentials are correct
3. Clear localStorage and try again
4. Check browser console for error details

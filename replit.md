# replit.md

## Overview

This is a stock market screening and analysis application. It provides a dashboard for filtering and viewing stocks based on technical indicators (RSI, SMA, price, volume, sector), displaying historical price charts, and fetching real-time data from Yahoo Finance. The application follows a full-stack TypeScript architecture with a React frontend and Express backend, using PostgreSQL for data persistence.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Routing**: Wouter (lightweight client-side routing)
- **State Management**: TanStack React Query for server state caching and synchronization
- **Styling**: Tailwind CSS with CSS custom properties for theming (dark financial theme)
- **UI Components**: shadcn/ui component library built on Radix UI primitives
- **Charts**: Recharts for rendering financial area charts with historical price data
- **Build Tool**: Vite with hot module replacement

### Backend Architecture
- **Framework**: Express.js with TypeScript
- **API Design**: RESTful endpoints defined in `shared/routes.ts` with Zod schemas for type-safe contracts
- **Database ORM**: Drizzle ORM with PostgreSQL dialect
- **External Data**: Yahoo Finance integration via `yahoo-finance2` package for live stock data updates

### Data Storage
- **Database**: PostgreSQL accessed via `pg` connection pool
- **Schema Location**: `shared/schema.ts` defines two tables:
  - `stocks`: Current stock snapshots with price, volume, technical indicators (RSI, SMA50, SMA200)
  - `historicalPrices`: OHLCV data for charting
- **Migrations**: Drizzle Kit manages schema migrations in `./migrations`

### Code Organization
- `client/`: Frontend React application
  - `src/components/`: UI components including stock filters and charts
  - `src/pages/`: Page components (Dashboard, 404)
  - `src/hooks/`: Custom React hooks for data fetching
  - `src/components/ui/`: shadcn/ui component library
- `server/`: Backend Express application
  - `routes.ts`: API endpoint handlers
  - `storage.ts`: Database access layer with filtering logic
  - `db.ts`: Database connection setup
- `shared/`: Shared code between frontend and backend
  - `schema.ts`: Drizzle table definitions and Zod schemas
  - `routes.ts`: API contract definitions with Zod validation

### API Endpoints
- `GET /api/stocks`: List stocks with optional filters (search, sector, price range, RSI range, volume, SMA200 position)
- `GET /api/stocks/:symbol`: Get single stock details (triggers Yahoo Finance update)
- `GET /api/stocks/:symbol/history`: Get historical price data for charts

### Build Process
- Development: Vite dev server with Express backend via `tsx`
- Production: Custom build script (`script/build.ts`) using esbuild for server bundling and Vite for client, outputting to `dist/`

## External Dependencies

### Database
- **PostgreSQL**: Required via `DATABASE_URL` environment variable
- Connection pooling via `pg` package
- Session storage via `connect-pg-simple`

### External APIs
- **Yahoo Finance**: `yahoo-finance2` package for fetching real-time stock quotes and historical data

### Key NPM Packages
- `drizzle-orm` / `drizzle-kit`: Database ORM and migration tooling
- `@tanstack/react-query`: Server state management
- `recharts`: Financial charting library
- `zod`: Runtime type validation for API contracts
- `wouter`: Client-side routing
- Radix UI primitives: Accessible component foundations
# Aureon — Frontend

Next.js 14 + TypeScript web application.

## Setup

```bash
cd frontend
npm install
cp .env.example .env.local
```

## Development

```bash
npm run dev          # Start dev server on http://localhost:3000
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript compiler checks
npm run format       # Format code with Prettier
```

## Build

```bash
npm run build        # Production build
npm run start        # Start production server
```

## Structure

```
src/
├── app/             → App Router pages and layouts
│   ├── layout.tsx   → Root layout
│   ├── page.tsx     → Home page
│   └── globals.css  → Global styles
├── components/      → Reusable UI components
├── hooks/           → Custom React hooks
├── lib/             → Utility functions and API clients
└── types/           → Shared TypeScript type definitions
```

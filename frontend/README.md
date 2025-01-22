# Invoice Payment Agent Frontend

A modern web interface for managing and monitoring automated invoice payments. Built with Next.js 14, TypeScript, and Shadcn UI components.

## Features

- 📊 **Dashboard Overview**: Real-time monitoring of invoice processing status
- 📬 **Email Monitoring**: View incoming invoice emails and their processing status
- 📄 **Invoice Management**: Review and manage processed invoices
- 💳 **Payment Tracking**: Monitor payment status and history
- 🔍 **Search & Filter**: Advanced search capabilities for invoices and payments
- 📱 **Responsive Design**: Fully responsive interface for all devices

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **UI Components**: Shadcn UI
- **State Management**: React Hooks
- **API Integration**: REST API with backend
- **Styling**: CSS Modules
- **Authentication**: NextAuth.js

## Getting Started

### Prerequisites

- Node.js 18.17 or later
- npm or yarn package manager
- Backend API running locally or deployed

### Installation

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd frontend
   ```

2. **Install Dependencies**
   ```bash
   npm install
   # or
   yarn install
   ```

3. **Environment Setup**
   ```bash
   # Copy example configuration
   cp .env.local.example .env.local

   # Configure environment variables:
   # - NEXT_PUBLIC_API_URL=http://localhost:8000
   # - NEXTAUTH_SECRET=your-secret
   # - NEXTAUTH_URL=http://localhost:3000
   ```

4. **Run Development Server**
   ```bash
   npm run dev
   # or
   yarn dev
   ```

   Open [http://localhost:3000](http://localhost:3000) to view the application.

## Project Structure

```
frontend/
├── app/                  # Next.js app directory
│   ├── layout.tsx       # Root layout
│   ├── page.tsx         # Home page
│   ├── dashboard/       # Dashboard routes
│   ├── invoices/        # Invoice management
│   └── payments/        # Payment tracking
├── components/          # Reusable components
│   ├── ui/             # Shadcn components
│   └── custom/         # Custom components
├── hooks/              # Custom React hooks
├── lib/               # Utility functions
└── public/            # Static assets
```

## Available Scripts

- `npm run dev`: Start development server
- `npm run build`: Build production application
- `npm run start`: Start production server
- `npm run lint`: Run ESLint
- `npm run type-check`: Run TypeScript compiler check

## Component Library

We use Shadcn UI components. To add new components:

```bash
npx shadcn@latest add [component-name]
```

Available components can be found in the `components/ui` directory.

## API Integration

The frontend communicates with the backend through REST APIs:

- `/api/invoices`: Invoice management endpoints
- `/api/payments`: Payment processing endpoints
- `/api/emails`: Email monitoring endpoints

## State Management

- React Query for server state
- React Context for global UI state
- Local state with useState for component-level state

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## Development Guidelines

- Follow TypeScript best practices
- Use functional components and hooks
- Implement proper error handling
- Write clean, documented code
- Follow the existing project structure

## Troubleshooting

### Common Issues

1. **Build Errors**
   - Clear `.next` directory
   - Remove `node_modules` and reinstall
   - Check TypeScript errors

2. **API Connection Issues**
   - Verify backend is running
   - Check environment variables
   - Confirm CORS settings

## License

This project is licensed under the MIT License.

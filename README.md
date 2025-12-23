# Juan365 Creative Ticketing System

A comprehensive ticketing and task management system for creative teams, featuring two-step approval workflows, real-time Telegram notifications, and analytics dashboard.

## Live Demo

- **Frontend**: https://juan365-ticketing-frontend.vercel.app
- **Backend API**: https://juan365-task-monitoring-production.up.railway.app

## Features

### Core Features
- **Task Management**: Create, assign, approve, and track tickets
- **Two-Step Approval Workflow**: Department Manager → Creative Manager approval
- **User Roles**: Admin, Manager, Member with role-based permissions
- **Real-time Notifications**: Telegram notifications with @mentions
- **File Management**: Upload and manage attachments (images, PDFs, documents)
- **Analytics Dashboard**: Visual charts showing ticket statistics
- **Activity Logs**: Full audit trail of all actions
- **Comment System**: Threaded comments with replies
- **History & Rollback**: View ticket history and restore previous states

### Dashboard Statistics
The dashboard displays 8 status cards:
| Status | Description |
|--------|-------------|
| Total | All tickets in the system |
| Dept Approval | Awaiting department manager approval |
| Creative Approval | Awaiting creative team approval |
| Approved | Fully approved, ready to assign |
| In Progress | Currently being worked on |
| Completed | Work finished, awaiting confirmation |
| Rejected | Declined tickets |
| Overdue | Past deadline |

## Tech Stack

### Backend
- **Framework**: Django 5.0 + Django REST Framework
- **Database**: SQLite (dev) / PostgreSQL (prod via Railway)
- **Authentication**: JWT (SimpleJWT)
- **Static Files**: WhiteNoise
- **Notifications**: Telegram Bot API

### Frontend
- **Framework**: React 18 with Vite
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **HTTP Client**: Axios
- **Routing**: React Router v6
- **Hosting**: Vercel

## Project Structure

```
ticketing-system/
├── backend/                    # Django REST API
│   ├── api/                    # Main API app
│   │   ├── models.py           # User, Ticket, Comment models
│   │   ├── views.py            # API viewsets
│   │   ├── serializers.py      # DRF serializers
│   │   └── permissions.py      # Custom permissions
│   ├── notifications/          # Telegram integration
│   │   └── telegram.py         # Telegram bot functions
│   └── ticketing/              # Django settings
│       ├── settings.py
│       └── urls.py
├── frontend/                   # React frontend
│   └── src/
│       ├── components/         # Reusable components
│       ├── pages/              # Page components
│       │   ├── Dashboard.jsx
│       │   ├── Tickets.jsx
│       │   ├── TicketDetail.jsx
│       │   └── Users.jsx
│       ├── context/            # Auth context
│       └── services/           # API services
├── docker-compose.yml          # Docker configuration
└── README.md
```

## Ticket Workflow

### Status Flow
```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  REQUESTED  │ ──► │ PENDING_CREATIVE │ ──► │     APPROVED     │
│ (For Dept   │     │ (For Creative    │     │                  │
│  Approval)  │     │  Approval)       │     │                  │
└─────────────┘     └──────────────────┘     └──────────────────┘
      │                                              │
      │ Reject                                       │ Assign
      ▼                                              ▼
┌─────────────┐                              ┌──────────────────┐
│  REJECTED   │                              │   IN_PROGRESS    │
└─────────────┘                              └──────────────────┘
                                                     │
                                                     │ Complete
                                                     ▼
                                             ┌──────────────────┐
                                             │    COMPLETED     │
                                             └──────────────────┘
```

### Two-Step Approval Process
1. **Member** creates a ticket → Status: `requested` (For Dept Approval)
2. **Department Manager** approves → Status: `pending_creative` (For Creative Approval)
3. **Creative Manager** approves → Status: `approved`
4. **Manager** assigns to a member → Status: `approved` (assigned)
5. **Assignee** starts work → Status: `in_progress`
6. **Assignee** completes work → Status: `completed`
7. **Requester** confirms completion → Ticket closed

## User Roles & Permissions

| Role | Permissions |
|------|------------|
| **Admin** | Full access: manage users, all tickets, system settings |
| **Manager** | Approve/reject tickets, assign tasks, manage department members |
| **Member** | Create tickets, view assigned tasks, update own tickets |

### Department-Based Access
- Managers can only approve tickets for their department
- Creative department has final approval authority
- Members see tickets they created or are assigned to

## API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login/` | POST | Login with username/password |
| `/api/auth/register/` | POST | Register new account |
| `/api/auth/token/refresh/` | POST | Refresh JWT token |
| `/api/auth/change-password/` | POST | Change password |

### Tickets
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tickets/` | GET | List all tickets (filtered by role) |
| `/api/tickets/` | POST | Create new ticket |
| `/api/tickets/{id}/` | GET | Get ticket details |
| `/api/tickets/{id}/` | PATCH | Update ticket |
| `/api/tickets/{id}/approve/` | POST | Approve ticket |
| `/api/tickets/{id}/reject/` | POST | Reject ticket |
| `/api/tickets/{id}/assign/` | POST | Assign to user |
| `/api/tickets/{id}/start/` | POST | Start working |
| `/api/tickets/{id}/complete/` | POST | Mark as complete |
| `/api/tickets/{id}/confirm/` | POST | Confirm completion |
| `/api/tickets/{id}/comments/` | GET/POST | List/add comments |
| `/api/tickets/{id}/attachments/` | POST | Upload attachment |
| `/api/tickets/{id}/history/` | GET | Get ticket history |
| `/api/tickets/{id}/rollback/` | POST | Rollback to previous state |

### Dashboard
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/stats/` | GET | Get dashboard statistics |
| `/api/dashboard/my-tasks/` | GET | Get assigned tasks |

### Users
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users/` | GET | List all users |
| `/api/users/{id}/` | PATCH | Update user |
| `/api/users/{id}/reset-password/` | POST | Reset user password |

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL (for production)

### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Docker Setup
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

## Environment Variables

### Backend (.env)
```env
# Django
DJANGO_SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/database

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_GROUP_CHAT_ID=-1001234567890
TELEGRAM_BOT_USERNAME=YourBotName

# Frontend URL (for notification links)
FRONTEND_URL=https://your-frontend.vercel.app
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000/api
```

## Deployment

### Backend (Railway)
1. Create a new Railway project
2. Add PostgreSQL database
3. Connect GitHub repository
4. Set environment variables
5. Deploy

### Frontend (Vercel)
1. Import GitHub repository
2. Set `VITE_API_URL` environment variable
3. Deploy

### Docker Production
```bash
docker-compose -f docker-compose.yml up -d
```

## Telegram Integration

### Setup
1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Get the bot token
3. Add bot to your notification group
4. Get group chat ID:
   ```bash
   python manage.py get_telegram_chat_id
   ```
5. Set environment variables

### Notification Types
- New ticket requests
- Approval/rejection notifications
- Assignment notifications
- Comment alerts
- Deadline reminders
- Completion confirmations

### User Mentions
Users with `telegram_id` set will be @mentioned in group notifications.

## Default Credentials

After initial setup:
- **Username**: `admin`
- **Password**: Set during `createsuperuser`

## Screenshots

### Dashboard
- 8 status cards showing ticket counts
- Pie chart: Tickets by status
- Bar chart: Tickets by priority
- Line chart: Weekly trends

### Ticket Detail
- Full ticket information
- Comments with replies
- File attachments
- Action buttons (Approve, Reject, Assign, etc.)
- History & Rollback

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details.

---

Built with Django + React by Juan365 Team

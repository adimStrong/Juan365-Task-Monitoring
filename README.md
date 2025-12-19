# Juan365 Task Monitoring System

A comprehensive ticketing and task management system for teams, featuring task allocation, approval workflows, real-time notifications, and file management.

## Features

- **Task Management**: Create, assign, approve, and track tickets
- **Approval Workflow**: Request -> Approval -> In Progress -> Completed
- **User Roles**: Admin, Manager, Member with role-based permissions
- **Notifications**: Real-time Telegram and in-app notifications
- **File Management**: Upload and manage images, videos, and documents
- **Analytics Dashboard**: Visual charts and statistics
- **Activity Logs**: Full audit trail of all actions

## Tech Stack

### Backend
- Django 5.0 + Django REST Framework
- SQLite (dev) / PostgreSQL (prod)
- Celery + Redis for background tasks
- JWT Authentication

### Frontend
- React 18 with Vite
- Tailwind CSS
- Recharts for analytics

### File Portal (Streamlit)
- Streamlit web interface
- Support for images, videos, documents
- Up to 500MB file uploads

## Project Structure

```
ticketing-system/
├── backend/              # Django REST API
│   ├── api/              # Main API app
│   ├── notifications/    # Telegram bot integration
│   └── ticketing/        # Django settings
├── frontend/             # React frontend
│   └── src/
│       ├── components/
│       ├── pages/
│       └── services/
├── streamlit_app/        # File upload portal
│   └── pages/
└── postman/              # API collection
```

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Streamlit File Portal
```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

## API Endpoints

- `POST /api/auth/login/` - Login
- `POST /api/auth/register/` - Register
- `GET /api/tickets/` - List tickets
- `POST /api/tickets/` - Create ticket
- `POST /api/tickets/{id}/approve/` - Approve ticket
- `POST /api/tickets/{id}/assign/` - Assign ticket
- `GET /api/dashboard/stats/` - Dashboard stats

## Default Credentials

- Username: `admin`
- Password: Set during setup

## Telegram Notifications

The system integrates with Telegram for real-time notifications:
- New ticket requests
- Approval/rejection notifications
- Assignment notifications
- Comment alerts
- Deadline reminders

## License

MIT License

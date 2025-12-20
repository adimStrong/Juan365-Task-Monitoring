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

### Telegram Setup

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather)
2. Get the bot token
3. Add the bot to your notification group
4. Get the group chat ID using:
   ```bash
   python manage.py get_telegram_chat_id
   ```
5. Set up the webhook:
   ```bash
   python manage.py setup_telegram_webhook --url https://your-domain.com/api/telegram/webhook/
   ```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot API token from BotFather | `123456:ABC-DEF...` |
| `TELEGRAM_GROUP_CHAT_ID` | Group chat ID for notifications | `-1001234567890` |
| `TELEGRAM_BOT_USERNAME` | Bot username (without @) | `Juan365Bot` |
| `FRONTEND_URL` | Frontend URL for ticket links | `https://your-app.vercel.app` |

### Telegram Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/telegram/connect/` | POST | Generate connection code |
| `/api/telegram/status/` | GET | Check connection status |
| `/api/telegram/disconnect/` | POST | Disconnect Telegram |
| `/api/telegram/test/` | POST | Send test notification |
| `/api/telegram/preferences/` | GET/PATCH | Notification preferences |
| `/api/telegram/webhook/` | POST | Telegram webhook (internal) |

## License

MIT License

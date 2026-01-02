# Juan365 Creative Ticketing System
## Complete Documentation

**Version:** 1.0
**Last Updated:** January 2026
**Organization:** Juan365 Creative Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Getting Started](#2-getting-started)
3. [User Guide](#3-user-guide)
4. [Ticket Workflow](#4-ticket-workflow)
5. [Technical Documentation](#5-technical-documentation)
6. [API Reference](#6-api-reference)
7. [Admin Guide](#7-admin-guide)
8. [Deployment & Configuration](#8-deployment--configuration)
9. [Appendix](#9-appendix)

---

# 1. Executive Summary

## Overview

The **Juan365 Creative Ticketing System** is a comprehensive task management platform designed specifically for creative teams. It features multi-step approval workflows, real-time Telegram notifications, detailed analytics, and role-based access control.

## Key Features at a Glance

| Feature | Description |
|---------|-------------|
| **Two-Step Approval** | Department Manager → Creative Manager workflow |
| **Real-time Notifications** | Telegram bot with @mentions |
| **Analytics Dashboard** | Performance metrics, charts, and team statistics |
| **Multi-Product Support** | Ads and Telegram products with quantities |
| **File Management** | Upload images, PDFs, and documents |
| **Activity Logging** | Full audit trail with rollback capability |
| **Threaded Comments** | Discussion threads on each ticket |
| **Soft Delete & Recovery** | Trash management with restore |

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19 + Vite + Tailwind CSS |
| **Backend** | Django 5.0 + Django REST Framework |
| **Database** | PostgreSQL |
| **Authentication** | JWT (SimpleJWT) |
| **File Storage** | Cloudinary (production) |
| **Notifications** | Telegram Bot API |
| **Hosting** | Railway (Backend) + Vercel (Frontend) |

## Live Deployment

| Environment | URL |
|-------------|-----|
| **Frontend** | https://juan365-ticketing-frontend.vercel.app |
| **Backend API** | https://juan365-task-monitoring-production.up.railway.app |
| **Repository** | https://github.com/adimStrong/Juan365-Task-Monitoring |

---

# 2. Getting Started

## 2.1 Registration & Login

### Creating an Account

1. Navigate to the login page
2. Click **"Register"** to create a new account
3. Fill in the required fields:
   - Username
   - Email
   - Password (minimum 8 characters)
   - First Name / Last Name
4. Submit the registration form
5. **Wait for admin approval** - Your account must be approved before you can log in

### Logging In

1. Enter your username and password
2. Click **"Login"**
3. If successful, you'll be redirected to the Dashboard

### Account Security

- **3 failed attempts** will lock your account for 30 minutes
- Contact an admin to unlock your account if needed
- Use "Contact Admin" link on login page for password issues

## 2.2 User Roles

The system has three user roles with different permissions:

| Role | Description | Permissions |
|------|-------------|-------------|
| **Admin** | System administrator | Full access to all features, user management, all approvals |
| **Manager** (Approver) | Department manager | Approve/reject tickets, assign tasks, view team analytics |
| **Member** | Team member | Create tickets, view assigned tasks, comment on tickets |

## 2.3 Dashboard Overview

The Dashboard is your home screen showing:

### Status Cards (8 total)

| Card | Description | Color |
|------|-------------|-------|
| **Total** | All tickets in the system | Blue |
| **Dept Approval** | Awaiting department manager approval | Blue |
| **Creative Approval** | Awaiting creative team approval | Purple |
| **Not Yet Started** | Approved but not started | Cyan |
| **In Progress** | Currently being worked on | Yellow |
| **Completed** | Work finished | Green |
| **Rejected** | Declined tickets | Gray |
| **Overdue** | Past deadline | Red |

### My Tasks Section

Shows your assigned tickets with quick action buttons.

### Charts

- **Pie Chart**: Tickets by status
- **Bar Chart**: Tickets by priority
- **Line Chart**: Weekly trends

---

# 3. User Guide

## 3.1 Creating a Ticket

### Step 1: Click "Create Ticket"

Navigate to the Create Ticket page from the sidebar or Dashboard.

### Step 2: Fill in Ticket Details

| Field | Description | Required |
|-------|-------------|----------|
| **Title** | Brief description of the task | Yes |
| **Description** | Detailed requirements | Yes |
| **Priority** | Low, Medium, High, or Urgent | Yes |
| **Department** | Target department | Yes |
| **Request Type** | Type of creative work | Yes |
| **Product** | Associated product/brand | Optional |

### Step 3: Choose Request Type

| Request Type | Description | Special Fields |
|--------------|-------------|----------------|
| **Socmed Posting** | Social media content | File Format dropdown |
| **Website Banner** | Web banners (H5 & WEB) | Criteria (Image/Video) |
| **Photoshoot** | Photography requests | Scheduled times |
| **Videoshoot** | Video production | Scheduled times |
| **Live Production** | Live streaming | Scheduled times |
| **Ads** | Advertising creatives | Multi-product selection |
| **Telegram** | Telegram channel content | Product + criteria |

### Step 4: Assign Creative Members (Optional)

- Select one or more Creative department members
- First selected = main assignee
- Additional = collaborators

### Step 5: Add Attachments (Optional)

- Drag & drop or click to upload files
- Supported: Images, PDFs, Documents
- Preview thumbnails shown before submission

### Step 6: Submit

Click **"Create Ticket"** to submit for approval.

## 3.2 Managing Tickets

### Viewing Tickets

- **Table View**: Detailed list with columns
- **Card View**: Visual cards with previews
- **Filters**: Status, Priority, Department, Assigned To

### Ticket Actions by Role

| Action | Who Can Do It | When |
|--------|---------------|------|
| **Approve** | Manager | When status is "Requested" or "Pending Creative" |
| **Reject** | Manager | Any time before completion |
| **Assign** | Manager | After approval, before "In Progress" |
| **Start Editing** | Assigned User | After assignment |
| **Mark Complete** | Assigned User | When in progress |
| **Confirm** | Requester | When completed |
| **Request Revision** | Requester | When completed |

### Comments & Discussion

- Add comments to discuss ticket details
- Reply to existing comments (threaded)
- All users with access can comment

### Attachments

- Upload additional files any time
- View/download existing attachments
- Preview images directly in browser

## 3.3 Notifications

### In-App Notifications

- Bell icon in header shows unread count
- Click to view all notifications
- Mark as read individually or all at once

### Telegram Notifications

If your Telegram ID is configured, you'll receive:

| Event | Notification |
|-------|--------------|
| New ticket assigned | Direct message + group mention |
| Ticket approved/rejected | Status update alert |
| New comment | Comment notification |
| Deadline approaching | Reminder alert |
| Ticket completed | Completion summary with stats |

---

# 4. Ticket Workflow

## 4.1 Status Flow Diagram

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   REQUESTED  │────>│ PENDING_CREATIVE │────>│   APPROVED   │
│ (Dept Review)│     │ (Creative Review)│     │              │
└──────────────┘     └──────────────────┘     └──────┬───────┘
       │                      │                      │
       v                      v                      v
┌──────────────┐         ┌─────────┐         ┌──────────────┐
│   REJECTED   │         │REJECTED │         │ IN_PROGRESS  │
└──────────────┘         └─────────┘         └──────┬───────┘
                                                    │
                                                    v
                                             ┌──────────────┐
                                             │  COMPLETED   │
                                             └──────┬───────┘
                                                    │
                              ┌─────────────────────┴─────────────────────┐
                              v                                           v
                        [Requester                                  [Revision
                         Confirms]                                  Requested]
                                                                         │
                                                                         v
                                                                  ┌──────────────┐
                                                                  │ IN_PROGRESS  │
                                                                  └──────────────┘
```

## 4.2 Two-Step Approval Process

### Step 1: Department Manager Approval

1. Member creates a ticket → Status: `REQUESTED`
2. Department Manager reviews the request
3. **Approve**: Moves to `PENDING_CREATIVE`
4. **Reject**: Status becomes `REJECTED`

**Note**: Creative department members skip this step.

### Step 2: Creative Manager Approval

1. Creative Manager reviews the ticket
2. **Approve**: Status becomes `APPROVED`
3. **Reject**: Status becomes `REJECTED`

### After Approval

1. Manager assigns to Creative member(s)
2. Assignee clicks "Start Editing" → `IN_PROGRESS`
3. Assignee completes work → `COMPLETED`
4. Requester confirms → Ticket closed

## 4.3 Priority Levels & Deadlines

Deadlines are automatically calculated based on priority:

| Priority | Video Content | Image Content |
|----------|---------------|---------------|
| **Urgent** | 3 hours | 2 hours |
| **High** | 24 hours | 24 hours |
| **Medium** | 72 hours (3 days) | 72 hours |
| **Low** | 168 hours (7 days) | 168 hours |

## 4.4 Revision Workflow

1. Requester reviews completed work
2. If changes needed, click **"Request Revision"**
3. Add revision comments explaining changes
4. Ticket returns to `IN_PROGRESS`
5. Revision count increments
6. Assignee makes changes and completes again

---

# 5. Technical Documentation

## 5.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│  React 19 + Vite + Tailwind CSS                            │
│  Deployed on: Vercel                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS / REST API
                              │
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                              │
│  Django 5.0 + Django REST Framework                        │
│  Deployed on: Railway                                       │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              v               v               v
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   PostgreSQL    │ │   Cloudinary    │ │  Telegram Bot   │
│   Database      │ │   File Storage  │ │  Notifications  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## 5.2 Project Structure

```
ticketing-system/
├── backend/                    # Django REST API
│   ├── api/                    # Main application
│   │   ├── models.py           # 14 database models
│   │   ├── views.py            # API endpoints & logic
│   │   ├── serializers.py      # DRF serializers
│   │   ├── permissions.py      # Custom permissions
│   │   ├── urls.py             # Route definitions
│   │   ├── cache_utils.py      # Caching utilities
│   │   └── management/         # Custom commands
│   ├── notifications/          # Telegram integration
│   │   └── telegram.py         # Bot functions
│   ├── ticketing/              # Django settings
│   │   ├── settings.py
│   │   └── urls.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── manage.py
│
├── frontend/                   # React + Vite
│   ├── src/
│   │   ├── pages/              # 14 page components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── TicketList.jsx
│   │   │   ├── TicketDetail.jsx
│   │   │   ├── CreateTicket.jsx
│   │   │   ├── Analytics.jsx
│   │   │   ├── Users.jsx
│   │   │   ├── Admin.jsx
│   │   │   └── ...
│   │   ├── components/         # Reusable components
│   │   ├── context/            # Auth & Toast contexts
│   │   ├── services/           # API client (Axios)
│   │   └── hooks/              # Custom React hooks
│   ├── package.json
│   └── vite.config.js
│
├── docs/                       # Test documentation
└── docker-compose.yml          # Docker configuration
```

## 5.3 Database Models (14 Total)

### Core Models

#### User
Extended Django user with roles and department.

| Field | Type | Description |
|-------|------|-------------|
| `role` | CharField | admin, manager, member |
| `user_department` | ForeignKey | Assigned department |
| `telegram_id` | CharField | For notifications |
| `is_approved` | Boolean | Requires admin approval |
| `is_locked` | Boolean | Account lockout |
| `failed_login_attempts` | Integer | Login counter |

#### Department

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Unique name |
| `manager` | ForeignKey | Department manager |
| `is_creative` | Boolean | Creative dept flag |
| `is_active` | Boolean | Active status |

#### Product

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Product name |
| `category` | CharField | general, ads, telegram |
| `is_active` | Boolean | Active status |

#### Ticket (Main Model)

| Field | Type | Description |
|-------|------|-------------|
| `title` | CharField | Ticket title |
| `description` | TextField | Detailed description |
| `status` | CharField | Workflow status |
| `priority` | CharField | low, medium, high, urgent |
| `request_type` | CharField | Type of request |
| `criteria` | CharField | image or video |
| `quantity` | Integer | Output count (max 1000) |
| `requester` | ForeignKey | Creator |
| `assigned_to` | ForeignKey | Assigned user |
| `target_department` | ForeignKey | Target department |
| `ticket_product` | ForeignKey | Associated product |
| `deadline` | DateTime | Auto-calculated |
| `revision_count` | Integer | Revision counter |
| `is_deleted` | Boolean | Soft delete flag |

### Supporting Models

| Model | Purpose |
|-------|---------|
| `TicketProductItem` | Multi-product for Ads/Telegram |
| `TicketAnalytics` | Performance metrics |
| `TicketComment` | Threaded comments |
| `TicketAttachment` | File uploads |
| `TicketCollaborator` | Multi-user access |
| `Notification` | In-app alerts |
| `ActivityLog` | Audit trail |
| `FileAsset` | General file storage |
| `PasswordResetToken` | Password recovery |
| `LoginAttempt` | Security audit |

---

# 6. API Reference

## 6.1 Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register/` | POST | User registration |
| `/api/auth/login/` | POST | Login with JWT |
| `/api/auth/refresh/` | POST | Refresh token |
| `/api/auth/me/` | GET/PATCH | Current user profile |
| `/api/auth/forgot-password/` | POST | Request password reset |
| `/api/auth/reset-password/` | POST | Reset with token |

## 6.2 Tickets

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tickets/` | GET | List tickets (filtered by role) |
| `/api/tickets/` | POST | Create ticket |
| `/api/tickets/{id}/` | GET | Get ticket details |
| `/api/tickets/{id}/` | PATCH | Update ticket |
| `/api/tickets/{id}/approve/` | POST | Approve (2-step) |
| `/api/tickets/{id}/reject/` | POST | Reject with reason |
| `/api/tickets/{id}/assign/` | POST | Assign to user |
| `/api/tickets/{id}/start/` | POST | Start working |
| `/api/tickets/{id}/complete/` | POST | Mark complete |
| `/api/tickets/{id}/confirm/` | POST | Requester confirms |
| `/api/tickets/{id}/request_revision/` | POST | Request revision |
| `/api/tickets/{id}/comments/` | GET/POST | List/add comments |
| `/api/tickets/{id}/attachments/` | GET/POST | List/upload files |
| `/api/tickets/{id}/history/` | GET | Activity history |
| `/api/tickets/{id}/rollback/` | POST | Rollback to previous |
| `/api/tickets/{id}/soft_delete/` | POST | Move to trash |
| `/api/tickets/{id}/restore/` | POST | Restore from trash |
| `/api/tickets/trash/` | GET | List deleted tickets |

## 6.3 Users & Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users/` | GET | List approved users |
| `/api/users/manage/` | GET/POST | Admin user management |
| `/api/users/manage/{id}/approve/` | POST | Approve user |
| `/api/users/manage/{id}/change_role/` | POST | Change role |
| `/api/users/manage/{id}/unlock_account/` | POST | Unlock account |

## 6.4 Resources

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/departments/` | GET/POST | Departments CRUD |
| `/api/products/` | GET/POST | Products CRUD |

## 6.5 Dashboard & Analytics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/stats/` | GET | Dashboard statistics |
| `/api/dashboard/my-tasks/` | GET | User's assigned tasks |
| `/api/analytics/` | GET | Comprehensive analytics |
| `/api/notifications/` | GET | User notifications |
| `/api/activities/` | GET | Activity logs |
| `/api/health/` | GET | Health check |

---

# 7. Admin Guide

## 7.1 User Management

### Approving New Users

1. Go to **Users** page
2. Find pending users (Pending tab)
3. Click **"Approve"** to grant access
4. User can now log in

### Changing User Roles

1. Go to **Users** page
2. Find the user
3. Click **"Change Role"**
4. Select new role: Admin, Approver (Manager), or Member

### Unlocking Accounts

1. Go to **Users** page
2. Find locked user (lock icon)
3. Click **"Unlock Account"**

### Assigning Departments

1. Go to **Admin** → **Users** tab
2. Edit user
3. Select department from dropdown
4. Save changes

## 7.2 Department Management

### Creating a Department

1. Go to **Admin** → **Departments** tab
2. Click **"Add Department"**
3. Enter name and description
4. Assign a manager (optional)
5. Check **"Is Creative"** if this is the Creative department

### Setting Department Managers

1. Go to **Admin** → **Departments** tab
2. Edit department
3. Select manager from dropdown
4. Manager will now approve tickets for this department

## 7.3 Product Management

### Creating Products

1. Go to **Admin** → **Products** tab
2. Click **"Add Product"**
3. Enter name
4. Select category:
   - **General**: Regular products
   - **Ads**: For Ads request type
   - **Telegram**: For Telegram request type

### Product Categories

| Category | Used For | Example Products |
|----------|----------|------------------|
| General | Socmed, Website, etc. | Juan365, JuanBingo |
| Ads | Ads request type | FB VID, TIKTOK VID, FB STATIC |
| Telegram | Telegram request type | Juan365 TG, JuanBingo TG |

## 7.4 Trash Management

### Viewing Deleted Tickets

1. Go to **Trash** page
2. See all soft-deleted tickets
3. View deletion date and who deleted

### Restoring Tickets

1. Go to **Trash** page
2. Find the ticket
3. Click **"Restore"**
4. Ticket returns to its previous status

### Permanent Deletion (Admin Only)

1. Go to **Trash** page
2. Find the ticket
3. Click **"Delete Forever"**
4. Confirm deletion
5. **Warning**: This cannot be undone

---

# 8. Deployment & Configuration

## 8.1 Backend (Railway)

### Setup Steps

1. Create a Railway project
2. Add PostgreSQL database
3. Connect GitHub repository
4. Set environment variables (see below)
5. Deploy automatically from main branch

### Environment Variables

```env
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.railway.app

# Database (auto-set by Railway)
DATABASE_URL=postgresql://user:pass@host:5432/db

# CORS
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_GROUP_CHAT_ID=-1001234567890

# Frontend URL (for notification links)
FRONTEND_URL=https://your-frontend.vercel.app

# Cloudinary (file storage)
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
```

## 8.2 Frontend (Vercel)

### Setup Steps

1. Import GitHub repository
2. Set environment variable
3. Deploy automatically from main branch

### Environment Variables

```env
VITE_API_URL=https://your-backend.railway.app
```

## 8.3 Telegram Bot Setup

### Creating the Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow prompts to name your bot
4. Copy the bot token

### Getting Group Chat ID

1. Add bot to your notification group
2. Run command:
   ```bash
   python manage.py get_telegram_chat_id
   ```
3. Copy the chat ID (negative number)

### User Mentions

For users to be @mentioned in notifications:
1. Go to **Users** page
2. Edit user profile
3. Add their Telegram username (without @)

## 8.4 Local Development

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

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
docker-compose up -d
```

---

# 9. Appendix

## 9.1 Glossary

| Term | Definition |
|------|------------|
| **Ticket** | A request for creative work |
| **Requester** | User who created the ticket |
| **Assignee** | User assigned to complete the work |
| **Collaborator** | Additional user with ticket access |
| **Approver** | Manager who approves/rejects tickets |
| **Creative Department** | The department that produces creative work |
| **Criteria** | Whether output is Image or Video |
| **Quantity** | Number of creative outputs needed |
| **Rollback** | Restore ticket to previous state |
| **Soft Delete** | Move to trash (recoverable) |

## 9.2 Status Definitions

| Status | Display Name | Description |
|--------|--------------|-------------|
| `requested` | Dept Approval | Awaiting department manager |
| `pending_creative` | Creative Approval | Awaiting creative manager |
| `approved` | Not Yet Started | Ready for assignment/work |
| `rejected` | Rejected | Declined at any step |
| `in_progress` | In Progress | Work has started |
| `completed` | Completed | Work finished |

## 9.3 Request Types

| Type | Description | Special Behavior |
|------|-------------|------------------|
| `socmed_posting` | Social media content | File format selection |
| `website_banner` | Web banners | Criteria selection |
| `photoshoot` | Photography | Scheduled task |
| `videoshoot` | Video production | Scheduled task |
| `live_production` | Live streaming | Scheduled task |
| `ads` | Advertising | Multi-product, auto-criteria |
| `telegram_channel` | Telegram content | Multi-product |

## 9.4 Troubleshooting

### Can't Log In

1. Check if account is approved (contact admin)
2. Check if account is locked (3 failed attempts)
3. Verify username/password
4. Clear browser cache

### Tickets Not Showing

1. Check filters are cleared
2. Verify you have permission to view
3. Check if ticket is in Trash

### Notifications Not Working

1. Verify Telegram ID is set in profile
2. Check bot is added to group
3. Verify environment variables

### File Upload Failed

1. Check file size (max 10MB)
2. Verify file type is supported
3. Check Cloudinary configuration

---

## Document Information

| Field | Value |
|-------|-------|
| **Document Title** | Juan365 Creative Ticketing System - Complete Documentation |
| **Version** | 1.0 |
| **Created** | January 2026 |
| **Author** | Juan365 Development Team |
| **Status** | Production |

---

*Built with Django + React by Juan365 Team*

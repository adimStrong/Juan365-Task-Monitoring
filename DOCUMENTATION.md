# Juan365 Creative Ticketing System - Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Models](#database-models)
4. [API Endpoints](#api-endpoints)
5. [Frontend Pages](#frontend-pages)
6. [Ticket Workflow](#ticket-workflow)
7. [User Roles & Permissions](#user-roles--permissions)
8. [Request Types](#request-types)
9. [Analytics](#analytics)
10. [Deployment](#deployment)
11. [Environment Variables](#environment-variables)

---

## Overview

**Juan365 Creative Ticketing System** is a full-stack ticket management platform designed for creative teams with multi-approval workflows, real-time notifications, and comprehensive analytics.

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Django 5.0 + Django REST Framework |
| **Frontend** | React 19 + Vite + Tailwind CSS |
| **Database** | PostgreSQL |
| **Authentication** | JWT (SimpleJWT) |
| **Notifications** | Telegram Bot API |
| **File Storage** | Cloudinary (production) / Local (development) |
| **Deployment** | Railway (backend) + Vercel (frontend) |

### Live URLs

- **Frontend:** https://juan365-ticketing-frontend.vercel.app
- **Backend API:** https://juan365-task-monitoring-production.up.railway.app
- **Repository:** https://github.com/adimStrong/Juan365-Task-Monitoring

---

## Architecture

```
ticketing-system/
├── backend/                    # Django REST API
│   ├── api/                    # Main application
│   │   ├── models.py           # Database models (14 models)
│   │   ├── views.py            # API endpoints & business logic
│   │   ├── serializers.py      # DRF serializers
│   │   ├── permissions.py      # Custom permissions
│   │   └── urls.py             # Route definitions
│   ├── notifications/          # Telegram integration
│   └── ticketing/              # Django settings
│
├── frontend/                   # React + Vite
│   ├── src/
│   │   ├── pages/              # 14 page components
│   │   ├── components/         # Reusable UI components
│   │   ├── context/            # Auth & Toast contexts
│   │   └── services/           # API client (Axios)
│   └── package.json
│
└── docs/                       # Test documentation
```

---

## Database Models

### Core Models

#### 1. User
Extended Django user with role-based access control.

| Field | Type | Description |
|-------|------|-------------|
| `role` | CharField | `admin`, `manager`, `member` |
| `user_department` | ForeignKey | Assigned department |
| `telegram_id` | CharField | For Telegram notifications |
| `is_approved` | Boolean | Requires admin approval |
| `is_locked` | Boolean | Account lockout (3 failed attempts) |
| `failed_login_attempts` | Integer | Login attempt counter |

#### 2. Department

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Unique department name |
| `manager` | ForeignKey | Department manager (User) |
| `is_creative` | Boolean | Flag for Creative department |
| `is_active` | Boolean | Active status |

#### 3. Product

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField | Product name |
| `category` | CharField | `general`, `ads`, `telegram` |
| `is_active` | Boolean | Active status |

#### 4. Ticket (Main Model)

| Field | Type | Description |
|-------|------|-------------|
| `title` | CharField | Ticket title |
| `description` | TextField | Detailed description |
| `status` | CharField | Workflow status (see below) |
| `priority` | CharField | `low`, `medium`, `high`, `urgent` |
| `request_type` | CharField | Type of creative request |
| `criteria` | CharField | `image` or `video` |
| `quantity` | Integer | Number of outputs (max 1000) |
| `requester` | ForeignKey | User who created ticket |
| `assigned_to` | ForeignKey | Assigned creative team member |
| `target_department` | ForeignKey | Target department |
| `ticket_product` | ForeignKey | Associated product |
| `deadline` | DateTime | Auto-calculated deadline |
| `revision_count` | Integer | Number of revisions |
| `is_deleted` | Boolean | Soft delete flag |

**Status Values:**
- `requested` - For Department Approval
- `pending_creative` - For Creative Approval
- `approved` - Ready for assignment
- `rejected` - Rejected at any step
- `in_progress` - Being worked on
- `completed` - Work finished

#### 5. TicketProductItem
For Ads/Telegram requests with multiple products.

| Field | Type | Description |
|-------|------|-------------|
| `ticket` | ForeignKey | Parent ticket |
| `product` | ForeignKey | Selected product |
| `quantity` | Integer | Quantity for this product |
| `criteria` | CharField | Auto-set for Ads (VID=video, STATIC=image) |

#### 6. TicketAnalytics
Performance tracking for each ticket.

| Field | Type | Description |
|-------|------|-------------|
| `ticket` | OneToOne | Associated ticket |
| `time_to_acknowledge` | Integer | Seconds from assign to start |
| `time_to_complete` | Integer | Minutes to complete |
| `total_cycle_time` | Integer | Total processing time |

#### 7. Supporting Models

| Model | Purpose |
|-------|---------|
| `TicketComment` | Threaded comments with replies |
| `TicketAttachment` | File uploads |
| `TicketCollaborator` | Multi-user collaboration |
| `Notification` | In-app + Telegram notifications |
| `ActivityLog` | Audit trail with rollback snapshots |
| `FileAsset` | General file storage |
| `PasswordResetToken` | Password recovery |
| `LoginAttempt` | Security audit |

---

## API Endpoints

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register/` | POST | User registration |
| `/api/auth/login/` | POST | Login with JWT |
| `/api/auth/refresh/` | POST | Refresh token |
| `/api/auth/me/` | GET/PATCH | Current user profile |
| `/api/auth/forgot-password/` | POST | Request password reset |
| `/api/auth/reset-password/` | POST | Reset with token |

### Tickets

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tickets/` | GET | List tickets (role-filtered) |
| `/api/tickets/` | POST | Create ticket |
| `/api/tickets/{id}/` | GET/PATCH | Get/update ticket |
| `/api/tickets/{id}/approve/` | POST | Approve (2-step) |
| `/api/tickets/{id}/reject/` | POST | Reject ticket |
| `/api/tickets/{id}/assign/` | POST | Assign to creative |
| `/api/tickets/{id}/start/` | POST | Start working |
| `/api/tickets/{id}/complete/` | POST | Mark complete |
| `/api/tickets/{id}/confirm/` | POST | Requester confirms |
| `/api/tickets/{id}/request_revision/` | POST | Request revision |
| `/api/tickets/{id}/comments/` | GET/POST | Comments |
| `/api/tickets/{id}/attachments/` | GET/POST | Attachments |
| `/api/tickets/{id}/history/` | GET | Activity history |
| `/api/tickets/{id}/rollback/` | POST | Rollback to previous state |
| `/api/tickets/{id}/soft_delete/` | POST | Move to trash |
| `/api/tickets/{id}/restore/` | POST | Restore from trash |
| `/api/tickets/trash/` | GET | List deleted tickets |

### Users & Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users/` | GET | List approved users |
| `/api/users/manage/` | GET/POST | Admin user management |
| `/api/users/manage/{id}/approve/` | POST | Approve user |
| `/api/users/manage/{id}/change_role/` | POST | Change role |
| `/api/users/manage/{id}/unlock_account/` | POST | Unlock account |
| `/api/departments/` | GET/POST | Departments CRUD |
| `/api/products/` | GET/POST | Products CRUD |

### Dashboard & Analytics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/stats/` | GET | Dashboard statistics |
| `/api/dashboard/my-tasks/` | GET | User's assigned tasks |
| `/api/dashboard/overdue/` | GET | Overdue tickets |
| `/api/analytics/` | GET | Comprehensive analytics |
| `/api/notifications/` | GET | User notifications |
| `/api/activities/` | GET | Activity logs |

---

## Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Stats, charts, recent tasks |
| Ticket List | `/tickets` | Filterable ticket table/cards |
| Ticket Detail | `/tickets/:id` | Full ticket view with actions |
| Create Ticket | `/tickets/new` | Dynamic form by request type |
| Analytics | `/analytics` | Performance metrics (admin/manager) |
| Admin | `/admin` | User/department/product management |
| Users | `/users` | User approval and management |
| Notifications | `/notifications` | Notification center |
| Activity Log | `/activity` | Audit trail |
| Trash | `/trash` | Deleted tickets recovery |
| Login | `/login` | Authentication |
| Register | `/register` | User registration |

---

## Ticket Workflow

### Status Flow

```
┌──────────────┐     ┌──────────────────┐     ┌──────────┐
│   REQUESTED  │────>│ PENDING_CREATIVE │────>│ APPROVED │
│ (Dept Review)│     │ (Creative Review)│     │          │
└──────────────┘     └──────────────────┘     └────┬─────┘
       │                      │                    │
       v                      v                    v
┌──────────────┐         ┌─────────┐         ┌────────────┐
│   REJECTED   │         │REJECTED │         │IN_PROGRESS │
└──────────────┘         └─────────┘         └─────┬──────┘
                                                   │
                                                   v
                                             ┌───────────┐
                                             │ COMPLETED │
                                             └─────┬─────┘
                                                   │
                                    ┌──────────────┴──────────────┐
                                    v                             v
                              [Requester                    [Revision
                               Confirms]                    Requested]
                                                                 │
                                                                 v
                                                          ┌────────────┐
                                                          │IN_PROGRESS │
                                                          └────────────┘
```

### Two-Step Approval

1. **Department Manager Approval** (REQUESTED → PENDING_CREATIVE)
   - Requester's department manager reviews
   - Creative team members skip this step

2. **Creative Manager Approval** (PENDING_CREATIVE → APPROVED)
   - Creative department users give final approval
   - Ticket ready for assignment

### Deadline Calculation

| Priority | Video | Image/Still |
|----------|-------|-------------|
| Urgent | 3 hours | 2 hours |
| High | 24 hours | 24 hours |
| Medium | 72 hours | 72 hours |
| Low | 168 hours | 168 hours |

---

## User Roles & Permissions

| Role | Permissions |
|------|-------------|
| **Admin** | Full access, user management, all approvals, analytics |
| **Manager** | Approve tickets, assign tasks, view team analytics |
| **Member** | Create tickets, view assigned tasks, comment |

### Department-Based Access

- Users submit tickets to their own department only
- Admins can submit to any department
- Managers approve only within their department
- Creative department has final approval authority

---

## Request Types

| Type | Product Selection | Quantity | Criteria |
|------|-------------------|----------|----------|
| Socmed Posting | General dropdown | Per ticket | Auto (from file format) |
| Website Banner | General dropdown | Per ticket | Manual select |
| Photoshoot | General dropdown | Per ticket | Manual select |
| Videoshoot | General dropdown | Per ticket | Manual select |
| Live Production | General dropdown | Per ticket | Manual select |
| **Ads** | Multi-select Ads products | Per product | Auto (VID=video, STATIC=image) |
| **Telegram** | Select Telegram products | Per product | Manual select |

### Ads Products (stored in database)
- Juan365 FB VID
- Juan365 TIKTOK VID
- Juan365 FB STATIC
- JuanBINGO FB VID
- JuanBINGO TIKTOK VID
- DIGI ADS FB STATIC
- DIGI ADS FB VID

### Telegram Products (stored in database)
- Juan365 Telegram Channel
- JuanBingo Telegram Channel

---

## Analytics

### Summary Metrics
- Total tickets in date range
- Completed count & rate
- Total output quantity
- Average output per ticket

### Team Performance Table
| Metric | Description |
|--------|-------------|
| Assigned | Tickets assigned to user |
| Assigned Qty | Total quantity assigned |
| Completed | Tickets completed |
| Output | Total output produced |
| In Progress | Currently working |
| Completion Rate | Completed/Assigned % |
| Avg Processing | Average time to complete |
| Avg Ack Time | Time from assign to start |

### Breakdowns
- **By Priority:** Urgent, High, Medium, Low
- **By Request Type:** All 7 types with quantities
- **By Criteria:** Image vs Video counts
- **Ads Product Output:** Breakdown by Ads products
- **Telegram Product Output:** Breakdown by Telegram products

---

## Deployment

### Backend (Railway)

1. Push to GitHub repository
2. Railway auto-deploys from main branch
3. PostgreSQL database included
4. Environment variables in Railway dashboard

### Frontend (Vercel)

1. Push to GitHub repository
2. Vercel auto-deploys from main branch
3. Environment variables in Vercel settings

### Docker (Local Development)

```bash
docker-compose up --build
```

---

## Environment Variables

### Backend (.env)

```env
# Django
DJANGO_SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_GROUP_CHAT_ID=-1001234567890
TELEGRAM_BOT_USERNAME=YourBotName

# Frontend URL (for email links)
FRONTEND_URL=https://your-frontend.vercel.app

# Cloudinary (optional)
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
```

### Frontend (.env)

```env
VITE_API_URL=https://your-backend.railway.app
```

---

## Key Features Summary

| Feature | Description |
|---------|-------------|
| Two-Step Approval | Department → Creative workflow |
| Auto Deadline | Calculated from priority & media type |
| Multi-Product Support | Ads/Telegram with per-product quantities |
| Criteria Tracking | Image vs Video analytics |
| Soft Delete | Trash with restore capability |
| Rollback | Restore tickets to previous states |
| Collaborators | Multi-user ticket access |
| Threaded Comments | Replies to comments |
| File Attachments | Upload with preview |
| Telegram Notifications | Real-time alerts |
| Account Security | Lockout after failed attempts |
| Analytics Dashboard | Comprehensive reporting |

---

## Security Features

- JWT authentication with refresh tokens
- Account lockout after 3 failed attempts (30 min)
- User approval required before login
- Password reset with 24-hour expiration
- Login attempt tracking
- CORS protection
- HTTPS enforcement in production

---

*Last updated: December 26, 2025*

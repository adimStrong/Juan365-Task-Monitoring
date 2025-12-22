# Juan365 Creative Ticketing System - Session Summary

## Project Overview
A ticket management system for Juan365 with two-step approval workflow, department management, and user management.

**Repository:** https://github.com/adimStrong/Juan365-Task-Monitoring
**Frontend (Vercel):** https://juan365-ticketing-frontend.vercel.app
**Backend (Railway):** https://juan365-task-monitoring-production.up.railway.app

---

## Key Features Implemented

### 1. Two-Step Approval Workflow
- **Step 1:** Department Manager approves → Status becomes `pending_creative`
- **Step 2:** Creative Manager approves → Status becomes `approved`
- Creative Manager or Admin can skip Step 1 and approve directly
- Status colors: `pending_creative` = purple

### 2. Department Management (8 Departments)
| Department | Manager | Type |
|------------|---------|------|
| Business Development | bizdev_manager | Standard |
| Creative | creative_manager | Creative (is_creative=true) |
| Digital Ads | digitalads_manager | Standard |
| Livestream | livestream_manager | Standard |
| Marketing | Ghost 365 (xxxghstt) | Standard |
| Sales | sales_manager | Standard |
| SEO | seo_manager | Standard |
| Social Media | socialmedia_manager | Standard |

**All manager passwords:** `Manager123!`

### 3. User Management Permissions
- **Managers AND Admins can now:**
  - Approve new user registrations
  - Reject/deactivate users
  - Change user roles
  - Reactivate users
  - Reset passwords
  - Delete users

### 4. Department Dropdown for Users
- Users page now has department dropdown instead of text input
- Shows all active departments from API

---

## Recent Changes (This Session)

### Backend (`backend/api/views.py`)
1. Changed user management permissions from `IsAdminUser` to `IsManagerUser`
2. Fixed Dockerfile paths for Railway build context

### Frontend
1. Added `pending_creative` status with purple color
2. Added `getStatusText()` for better status labels
3. Added loading indicators for dropdowns in CreateTicket
4. Changed department field to dropdown in Users page

### Docker/Deployment
- Fixed `backend/Dockerfile` to use `backend/` prefix for paths (Railway build context is root)

---

## Database Credentials

### Production (Railway)
- **Admin:** username=`admin`, password=`admin123`
- **All Managers:** password=`Manager123!`
  - bizdev_manager, creative_manager, digitalads_manager
  - livestream_manager, sales_manager, seo_manager, socialmedia_manager

### Local (Docker)
- PostgreSQL: `postgres:postgres123@localhost:5432/ticketing`

---

## API Endpoints Reference

### Auth
- POST `/api/auth/login/` - Login
- POST `/api/auth/register/` - Register
- GET `/api/auth/me/` - Current user

### Tickets
- GET/POST `/api/tickets/` - List/Create
- GET/PATCH/DELETE `/api/tickets/{id}/` - Detail
- POST `/api/tickets/{id}/approve/` - Approve (managers/admins)
- POST `/api/tickets/{id}/reject/` - Reject
- POST `/api/tickets/{id}/assign/` - Assign
- POST `/api/tickets/{id}/start/` - Start work
- POST `/api/tickets/{id}/complete/` - Complete

### Users
- GET `/api/users/` - List active users
- GET/POST `/api/users/manage/` - Admin user list/create
- POST `/api/users/manage/{id}/approve/` - Approve user
- POST `/api/users/manage/{id}/reject_user/` - Deactivate
- POST `/api/users/manage/{id}/change_role/` - Change role

### Departments
- GET/POST `/api/departments/` - List/Create
- PATCH `/api/departments/{id}/` - Update (use `manager_id` to set manager)

---

## Files Modified This Session

```
backend/
├── api/views.py          # User management permissions (IsAdminUser → IsManagerUser)
├── Dockerfile            # Fixed paths for Railway (backend/ prefix)

frontend/src/
├── pages/
│   ├── TicketList.jsx    # Added pending_creative status color
│   ├── TicketDetail.jsx  # Added pending_creative handling
│   ├── Dashboard.jsx     # Added pending_creative status
│   ├── Users.jsx         # Department dropdown instead of text input
│   └── CreateTicket.jsx  # Loading indicators for dropdowns
└── services/api.js       # API service (unchanged)
```

---

## Commands Cheat Sheet

### Get Auth Token
```bash
curl -s https://juan365-task-monitoring-production.up.railway.app/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### List Departments
```bash
curl -s "https://juan365-task-monitoring-production.up.railway.app/api/departments/" \
  -H "Authorization: Bearer <TOKEN>"
```

### Create Department
```bash
curl -s -X POST "https://juan365-task-monitoring-production.up.railway.app/api/departments/" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name":"New Dept","description":"Description","is_creative":false,"is_active":true}'
```

### Assign Manager to Department
```bash
curl -s -X PATCH "https://juan365-task-monitoring-production.up.railway.app/api/departments/{id}/" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"manager_id": <user_id>}'
```

---

## Next Steps / Pending Items
- All tickets were cleared (fresh start)
- System ready for production use
- Test two-step approval workflow with real users

---

## Resume Prompt for Claude

When resuming, use this context:

> "Continue working on Juan365 Creative Ticketing System. Key context:
> - Two-step approval: Dept Manager → Creative Manager
> - 8 departments with managers assigned
> - Managers can now approve users (not just admins)
> - Frontend on Vercel, Backend on Railway
> - All tickets cleared, starting fresh"

---

*Last updated: December 22, 2025*

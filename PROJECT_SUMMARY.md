# Juan365 Ticketing System - Project Summary

**Repository:** https://github.com/adimStrong/Juan365-Task-Monitoring

**Location:** `C:\Users\us\Projects\ticketing-system`

## Stack
- **Backend:** Django REST Framework (`backend/`)
- **Frontend:** Streamlit (`streamlit_app/`)
- **Deployment:** Streamlit Cloud + Cloudflare Tunnel for backend

## Current Status - Working Features
- Dashboard with charts
- Create/View/Manage Tickets (Approve, Reject, Assign, Start, Complete)
- Comments & Attachments on tickets
- Create Users (admin)
- Approve Users (admin)
- Activity Logs
- My Tasks page
- Dedicated Ticket Detail page (hidden from sidebar)

## Pending Issue - Reset Password

1. API endpoint exists in `backend/api/views.py` (line 246-270) - `reset_password` action
2. URL is registered: `/api/users/manage/{id}/reset_password/`
3. **BUT:** Running Django server doesn't serve the endpoint (returns 404)
4. Django Admin models registered in `backend/api/admin.py` but not appearing in admin panel
5. **Workaround:** Use Django Admin at `http://localhost:8000/admin/` for password reset (once admin models appear)

## To Fix
1. Restart Django server properly to load new `admin.py`
2. Verify admin panel shows Users, Tickets, etc.
3. Test `reset_password` API endpoint
4. Optionally restore Streamlit reset password UI in `streamlit_app/pages/4_Activity_Users.py`

## Key Files
- `backend/api/views.py` - API endpoints including reset_password (line 246)
- `backend/api/admin.py` - Django admin registrations (Users, Tickets, etc.)
- `backend/ticketing/settings.py` - Django settings with CSRF/CORS config
- `streamlit_app/pages/4_Activity_Users.py` - User management UI
- `streamlit_app/utils/api_client.py` - API client with reset_user_password method

## Credentials
- **Admin:** username: `admin`, password: `admin123`
- **Cloudflare Tunnel URL:** Changes on restart (was `https://induced-intend-expert-designing.trycloudflare.com`)

## Commands
```bash
# Start Django backend
cd C:\Users\us\Projects\ticketing-system\backend
python manage.py runserver 0.0.0.0:8000

# Start Cloudflare tunnel
cloudflared tunnel --url http://localhost:8000
```

# Juan365 Ticketing System - Software Test Plan

**Document Version:** 1.0
**Date:** December 20, 2025
**Project:** Juan365 Ticketing System
**Standard:** IEEE 829-2008 / ISTQB Guidelines

---

## 1. INTRODUCTION

### 1.1 Purpose
This document defines the comprehensive testing strategy, test cases, and documentation for the Juan365 Ticketing System following industry-standard software testing practices.

### 1.2 Scope
- **Backend:** Django REST API (Authentication, Tickets, Users, Notifications, Activity)
- **Frontend:** React SPA (All pages, components, user flows)
- **Integration:** API-Frontend communication, Database operations
- **E2E:** Complete user workflows

### 1.3 Test Environment
| Environment | URL | Purpose |
|-------------|-----|---------|
| Production Frontend | https://juan365-ticketing-frontend.vercel.app | E2E Testing |
| Production Backend | https://juan365-task-monitoring-production.up.railway.app/api/ | API Testing |
| Local Backend | http://localhost:8000/api | Unit/Integration Testing |
| Local Frontend | http://localhost:5173 | Component Testing |

### 1.4 Test Credentials
| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| Test User | testuser1 | Test123! |

---

## 2. TEST STRATEGY

### 2.1 Testing Levels

| Level | Type | Tools | Coverage Target |
|-------|------|-------|-----------------|
| L1 | Unit Tests | pytest, Jest | 80% code coverage |
| L2 | Integration Tests | pytest, Playwright | API endpoints |
| L3 | System Tests | Playwright | User workflows |
| L4 | Acceptance Tests | Manual/Playwright | Business requirements |

### 2.2 Testing Types

1. **Functional Testing** - Verify features work as specified
2. **Security Testing** - Authentication, authorization, input validation
3. **Performance Testing** - Response times, load handling
4. **Usability Testing** - UI/UX consistency
5. **Regression Testing** - Ensure fixes don't break existing functionality

---

## 3. FILES TO CREATE

### 3.1 Backend Test Files
```
backend/
├── api/
│   └── tests/
│       ├── __init__.py
│       ├── test_auth.py          # Authentication tests
│       ├── test_users.py         # User management tests
│       ├── test_tickets.py       # Ticket CRUD tests
│       ├── test_ticket_actions.py # Ticket workflow tests
│       ├── test_comments.py      # Comments/replies tests
│       ├── test_attachments.py   # File upload tests
│       ├── test_collaborators.py # Collaborator tests
│       ├── test_notifications.py # Notification tests
│       ├── test_activity.py      # Activity log tests
│       ├── test_dashboard.py     # Dashboard API tests
│       └── test_permissions.py   # RBAC tests
├── conftest.py                   # Pytest fixtures
└── pytest.ini                    # Pytest configuration
```

### 3.2 Frontend Test Files
```
frontend/
├── src/
│   └── __tests__/
│       ├── components/
│       │   └── Layout.test.jsx
│       ├── pages/
│       │   ├── Login.test.jsx
│       │   ├── Register.test.jsx
│       │   ├── Dashboard.test.jsx
│       │   ├── TicketList.test.jsx
│       │   ├── TicketDetail.test.jsx
│       │   └── Users.test.jsx
│       └── services/
│           └── api.test.js
├── e2e/
│   ├── auth.spec.js              # Auth E2E tests
│   ├── tickets.spec.js           # Ticket E2E tests
│   ├── users.spec.js             # User management E2E
│   └── workflows.spec.js         # Complete workflow E2E
├── playwright.config.js
└── vitest.config.js
```

### 3.3 Documentation Files
```
docs/
├── TEST_PLAN.md                  # This document (detailed)
├── TEST_CASES.md                 # All test cases catalog
├── TEST_REPORT_TEMPLATE.md       # Test execution report template
└── DEFECT_REPORT_TEMPLATE.md     # Bug report template
```

---

## 4. BACKEND TEST CASES

### 4.1 Authentication Tests (TC-AUTH)

| ID | Test Case | Priority | Steps | Expected Result |
|----|-----------|----------|-------|-----------------|
| TC-AUTH-001 | User Registration | High | POST /auth/register/ with valid data | 201 Created, user pending approval |
| TC-AUTH-002 | Registration - Duplicate Username | High | Register with existing username | 400 Bad Request |
| TC-AUTH-003 | Registration - Invalid Email | Medium | Register with invalid email format | 400 Bad Request |
| TC-AUTH-004 | Registration - Weak Password | Medium | Register with password < 8 chars | 400 Bad Request |
| TC-AUTH-005 | Login - Valid Credentials | High | POST /auth/login/ with valid creds | 200 OK, tokens returned |
| TC-AUTH-006 | Login - Invalid Password | High | Login with wrong password | 401 Unauthorized |
| TC-AUTH-007 | Login - Unapproved User | High | Login before admin approval | 403 Forbidden |
| TC-AUTH-008 | Login - Inactive User | High | Login with deactivated account | 403 Forbidden |
| TC-AUTH-009 | Token Refresh | High | POST /auth/refresh/ with valid refresh token | 200 OK, new access token |
| TC-AUTH-010 | Token Refresh - Expired | Medium | Refresh with expired token | 401 Unauthorized |
| TC-AUTH-011 | Get Current User | Medium | GET /auth/me/ with valid token | 200 OK, user data |
| TC-AUTH-012 | Update Profile | Medium | PATCH /auth/me/ with valid data | 200 OK, updated user |

### 4.2 User Management Tests (TC-USER)

| ID | Test Case | Priority | Steps | Expected Result |
|----|-----------|----------|-------|-----------------|
| TC-USER-001 | List Users (Admin) | High | GET /users/manage/ as admin | 200 OK, all users |
| TC-USER-002 | List Users (Non-Admin) | High | GET /users/manage/ as member | 403 Forbidden |
| TC-USER-003 | Approve User | High | POST /users/manage/{id}/approve/ | 200 OK, user approved |
| TC-USER-004 | Reject User | High | POST /users/manage/{id}/reject_user/ | 200 OK, user deactivated |
| TC-USER-005 | Change Role | High | POST /users/manage/{id}/change_role/ | 200 OK, role updated |
| TC-USER-006 | Reactivate User | Medium | POST /users/manage/{id}/reactivate/ | 200 OK, user active |
| TC-USER-007 | Create User (Admin) | Medium | POST /users/manage/ as admin | 201 Created, auto-approved |
| TC-USER-008 | Filter by Approval Status | Medium | GET /users/manage/?is_approved=false | 200 OK, pending users |
| TC-USER-009 | Filter by Role | Medium | GET /users/manage/?role=manager | 200 OK, managers only |

### 4.3 Ticket Tests (TC-TICKET)

| ID | Test Case | Priority | Steps | Expected Result |
|----|-----------|----------|-------|-----------------|
| TC-TICKET-001 | Create Ticket | High | POST /tickets/ with valid data | 201 Created, status=requested |
| TC-TICKET-002 | Create - Missing Title | High | POST /tickets/ without title | 400 Bad Request |
| TC-TICKET-003 | List Own Tickets | High | GET /tickets/ as member | 200 OK, own tickets only |
| TC-TICKET-004 | List All Tickets (Manager) | High | GET /tickets/ as manager | 200 OK, all tickets |
| TC-TICKET-005 | Get Ticket Detail | High | GET /tickets/{id}/ | 200 OK, full details |
| TC-TICKET-006 | Update Ticket | Medium | PATCH /tickets/{id}/ | 200 OK, updated |
| TC-TICKET-007 | Delete Ticket | Medium | DELETE /tickets/{id}/ | 204 No Content |
| TC-TICKET-008 | Filter by Status | Medium | GET /tickets/?status=in_progress | 200 OK, filtered |
| TC-TICKET-009 | Filter by Priority | Medium | GET /tickets/?priority=urgent | 200 OK, filtered |
| TC-TICKET-010 | Search Tickets | Medium | GET /tickets/?search=keyword | 200 OK, matching |
| TC-TICKET-011 | Date Range Filter | Low | GET /tickets/?date_from=X&date_to=Y | 200 OK, in range |

### 4.4 Ticket Actions Tests (TC-ACTION)

| ID | Test Case | Priority | Steps | Expected Result |
|----|-----------|----------|-------|-----------------|
| TC-ACTION-001 | Approve Ticket | High | POST /tickets/{id}/approve/ as manager | 200 OK, status=approved |
| TC-ACTION-002 | Approve - Non-Manager | High | POST /tickets/{id}/approve/ as member | 403 Forbidden |
| TC-ACTION-003 | Reject Ticket | High | POST /tickets/{id}/reject/ with reason | 200 OK, status=rejected |
| TC-ACTION-004 | Assign Ticket | High | POST /tickets/{id}/assign/ with user_id | 200 OK, assigned |
| TC-ACTION-005 | Assign - Not Approved | Medium | Assign ticket in requested status | 400 Bad Request |
| TC-ACTION-006 | Start Work | High | POST /tickets/{id}/start/ | 200 OK, status=in_progress |
| TC-ACTION-007 | Start - Not Assigned | Medium | Start work on unassigned ticket | 400 Bad Request |
| TC-ACTION-008 | Complete Ticket | High | POST /tickets/{id}/complete/ | 200 OK, status=completed |
| TC-ACTION-009 | Confirm Completion | High | POST /tickets/{id}/confirm/ as requester | 200 OK, confirmed |
| TC-ACTION-010 | Confirm - Not Requester | Medium | Confirm as non-requester | 403 Forbidden |

### 4.5 Comments & Attachments Tests (TC-COMMENT, TC-ATTACH)

| ID | Test Case | Priority | Steps | Expected Result |
|----|-----------|----------|-------|-----------------|
| TC-COMMENT-001 | Add Comment | High | POST /tickets/{id}/comments/ | 201 Created |
| TC-COMMENT-002 | Reply to Comment | Medium | POST with parent_id | 201 Created, nested |
| TC-COMMENT-003 | List Comments | Medium | GET /tickets/{id}/comments/ | 200 OK, with replies |
| TC-ATTACH-001 | Upload Attachment | High | POST multipart/form-data | 201 Created |
| TC-ATTACH-002 | Delete Attachment | Medium | DELETE /attachments/{id}/ | 204 No Content |
| TC-ATTACH-003 | Delete - Not Owner | Medium | Delete other's attachment | 403 Forbidden |

### 4.6 Notifications & Activity Tests (TC-NOTIF, TC-ACTIVITY)

| ID | Test Case | Priority | Steps | Expected Result |
|----|-----------|----------|-------|-----------------|
| TC-NOTIF-001 | List Notifications | Medium | GET /notifications/ | 200 OK, user's notifications |
| TC-NOTIF-002 | Mark as Read | Medium | POST /notifications/{id}/read/ | 200 OK |
| TC-NOTIF-003 | Mark All Read | Medium | POST /notifications/read_all/ | 200 OK |
| TC-NOTIF-004 | Unread Count | Medium | GET /notifications/unread_count/ | 200 OK, count |
| TC-ACTIVITY-001 | List Activities | Medium | GET /activities/ | 200 OK, activities |
| TC-ACTIVITY-002 | Activity Created on Action | Medium | Perform ticket action | Activity logged |

### 4.7 Dashboard Tests (TC-DASH)

| ID | Test Case | Priority | Steps | Expected Result |
|----|-----------|----------|-------|-----------------|
| TC-DASH-001 | Get Stats | High | GET /dashboard/stats/ | 200 OK, stats object |
| TC-DASH-002 | My Tasks | Medium | GET /dashboard/my-tasks/ | 200 OK, assigned tickets |
| TC-DASH-003 | Team Overview | Medium | GET /dashboard/team-overview/ as manager | 200 OK |
| TC-DASH-004 | Overdue Tickets | Medium | GET /dashboard/overdue/ | 200 OK, overdue list |

---

## 5. FRONTEND E2E TEST CASES

### 5.1 Authentication Flow (E2E-AUTH)

| ID | Test Case | Priority |
|----|-----------|----------|
| E2E-AUTH-001 | Complete login flow with valid credentials |
| E2E-AUTH-002 | Login error display for invalid credentials |
| E2E-AUTH-003 | Registration flow with success message |
| E2E-AUTH-004 | Registration validation (password mismatch) |
| E2E-AUTH-005 | Logout clears session and redirects |
| E2E-AUTH-006 | Protected route redirects unauthenticated users |
| E2E-AUTH-007 | Token refresh on session timeout |

### 5.2 Ticket Workflow (E2E-TICKET)

| ID | Test Case | Priority |
|----|-----------|----------|
| E2E-TICKET-001 | Create ticket and verify in list |
| E2E-TICKET-002 | Search and filter tickets |
| E2E-TICKET-003 | View ticket details |
| E2E-TICKET-004 | Add comment to ticket |
| E2E-TICKET-005 | Reply to comment |
| E2E-TICKET-006 | Upload attachment |
| E2E-TICKET-007 | Complete ticket workflow (request→approve→assign→start→complete→confirm) |

### 5.3 User Management (E2E-USER)

| ID | Test Case | Priority |
|----|-----------|----------|
| E2E-USER-001 | Admin approves new user |
| E2E-USER-002 | Admin changes user role |
| E2E-USER-003 | Admin creates new user |
| E2E-USER-004 | Filter users by status |
| E2E-USER-005 | Non-admin cannot access user management |

### 5.4 Dashboard & Navigation (E2E-NAV)

| ID | Test Case | Priority |
|----|-----------|----------|
| E2E-NAV-001 | Dashboard loads with correct stats |
| E2E-NAV-002 | Navigation between all pages |
| E2E-NAV-003 | Notification badge updates |
| E2E-NAV-004 | Activity log displays actions |
| E2E-NAV-005 | Quick actions navigate correctly |

---

## 6. SECURITY TEST CASES (TC-SEC)

| ID | Test Case | Priority |
|----|-----------|----------|
| TC-SEC-001 | SQL Injection in search fields |
| TC-SEC-002 | XSS in ticket title/description |
| TC-SEC-003 | CSRF protection on mutations |
| TC-SEC-004 | JWT token validation |
| TC-SEC-005 | Authorization bypass attempts |
| TC-SEC-006 | File upload malware scanning |
| TC-SEC-007 | Rate limiting on login attempts |
| TC-SEC-008 | Sensitive data in responses (no passwords) |

---

## 7. PERFORMANCE TEST CASES (TC-PERF)

| ID | Test Case | Target |
|----|-----------|--------|
| TC-PERF-001 | Login response time | < 500ms |
| TC-PERF-002 | Dashboard load time | < 2s |
| TC-PERF-003 | Ticket list (100 items) | < 1s |
| TC-PERF-004 | File upload (5MB) | < 5s |
| TC-PERF-005 | Concurrent users (50) | No errors |

---

## 8. IMPLEMENTATION PLAN

### Phase 1: Setup & Backend Unit Tests
1. Create pytest configuration (`conftest.py`, `pytest.ini`)
2. Create test fixtures (users, tickets, etc.)
3. Implement TC-AUTH tests
4. Implement TC-USER tests
5. Implement TC-TICKET tests
6. Implement TC-ACTION tests

### Phase 2: Backend Integration & API Tests
1. Implement TC-COMMENT tests
2. Implement TC-ATTACH tests
3. Implement TC-NOTIF tests
4. Implement TC-ACTIVITY tests
5. Implement TC-DASH tests
6. Implement TC-SEC tests

### Phase 3: Frontend Unit Tests
1. Setup Vitest configuration
2. Create component test utilities
3. Implement Login/Register tests
4. Implement Dashboard tests
5. Implement TicketList/Detail tests
6. Implement Users tests

### Phase 4: E2E Tests
1. Setup Playwright configuration
2. Create test helpers and fixtures
3. Implement E2E-AUTH tests
4. Implement E2E-TICKET tests
5. Implement E2E-USER tests
6. Implement E2E-NAV tests

### Phase 5: Documentation & Reporting
1. Create TEST_CASES.md catalog
2. Create TEST_REPORT_TEMPLATE.md
3. Create DEFECT_REPORT_TEMPLATE.md
4. Generate test coverage report
5. Create final test summary

---

## 9. CRITICAL FILES TO MODIFY/CREATE

### Backend
- `C:\Users\us\Projects\ticketing-system\backend\conftest.py` - Pytest fixtures
- `C:\Users\us\Projects\ticketing-system\backend\pytest.ini` - Pytest config
- `C:\Users\us\Projects\ticketing-system\backend\api\tests\` - All test modules

### Frontend
- `C:\Users\us\Projects\ticketing-system\frontend\vitest.config.js` - Vitest config
- `C:\Users\us\Projects\ticketing-system\frontend\playwright.config.js` - E2E config
- `C:\Users\us\Projects\ticketing-system\frontend\e2e\` - E2E test files

### Documentation
- `C:\Users\us\Projects\ticketing-system\docs\TEST_PLAN.md`
- `C:\Users\us\Projects\ticketing-system\docs\TEST_CASES.md`
- `C:\Users\us\Projects\ticketing-system\docs\TEST_REPORT_TEMPLATE.md`

---

## 10. EXIT CRITERIA

Testing is complete when:
- [ ] All High priority test cases pass (100%)
- [ ] All Medium priority test cases pass (95%+)
- [ ] Code coverage ≥ 80%
- [ ] No Critical or High severity defects open
- [ ] All security test cases pass
- [ ] Performance targets met
- [ ] Test documentation complete

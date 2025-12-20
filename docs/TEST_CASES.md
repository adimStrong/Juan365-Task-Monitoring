# Juan365 Ticketing System - Test Cases Catalog

**Document Version:** 1.0
**Last Updated:** December 20, 2025

---

## Table of Contents
1. [Authentication Tests](#1-authentication-tests-tc-auth)
2. [User Management Tests](#2-user-management-tests-tc-user)
3. [Ticket Tests](#3-ticket-tests-tc-ticket)
4. [Ticket Action Tests](#4-ticket-action-tests-tc-action)
5. [Comment Tests](#5-comment-tests-tc-comment)
6. [Attachment Tests](#6-attachment-tests-tc-attach)
7. [Notification Tests](#7-notification-tests-tc-notif)
8. [Activity Log Tests](#8-activity-log-tests-tc-activity)
9. [Dashboard Tests](#9-dashboard-tests-tc-dash)
10. [E2E Tests](#10-e2e-tests)

---

## 1. Authentication Tests (TC-AUTH)

| ID | Test Case | Priority | Precondition | Steps | Expected Result |
|----|-----------|----------|--------------|-------|-----------------|
| TC-AUTH-001 | User Registration | High | None | POST /auth/register/ with valid data | 201 Created, user pending approval |
| TC-AUTH-002 | Registration - Duplicate Username | High | User exists | Register with existing username | 400 Bad Request |
| TC-AUTH-003 | Registration - Invalid Email | Medium | None | Register with invalid email format | 400 Bad Request |
| TC-AUTH-004 | Registration - Weak Password | Medium | None | Register with password < 8 chars | 400 Bad Request |
| TC-AUTH-005 | Login - Valid Credentials | High | Approved user exists | POST /auth/login/ with valid creds | 200 OK, tokens returned |
| TC-AUTH-006 | Login - Invalid Password | High | User exists | Login with wrong password | 401 Unauthorized |
| TC-AUTH-007 | Login - Unapproved User | High | Unapproved user exists | Login before admin approval | 403 Forbidden |
| TC-AUTH-008 | Login - Inactive User | High | Inactive user exists | Login with deactivated account | 403 Forbidden |
| TC-AUTH-009 | Token Refresh | High | Valid refresh token | POST /auth/refresh/ | 200 OK, new access token |
| TC-AUTH-010 | Token Refresh - Expired | Medium | Expired token | Refresh with expired token | 401 Unauthorized |
| TC-AUTH-011 | Get Current User | Medium | Authenticated | GET /auth/me/ with valid token | 200 OK, user data |
| TC-AUTH-012 | Update Profile | Medium | Authenticated | PATCH /auth/me/ with valid data | 200 OK, updated user |

---

## 2. User Management Tests (TC-USER)

| ID | Test Case | Priority | Precondition | Steps | Expected Result |
|----|-----------|----------|--------------|-------|-----------------|
| TC-USER-001 | List Users (Admin) | High | Admin authenticated | GET /users/manage/ | 200 OK, all users |
| TC-USER-002 | List Users (Non-Admin) | High | Member authenticated | GET /users/manage/ | 403 Forbidden |
| TC-USER-003 | Approve User | High | Pending user exists | POST /users/manage/{id}/approve/ | 200 OK, user approved |
| TC-USER-004 | Reject User | High | User exists | POST /users/manage/{id}/reject_user/ | 200 OK, user deactivated |
| TC-USER-005 | Change Role | High | User exists | POST /users/manage/{id}/change_role/ | 200 OK, role updated |
| TC-USER-006 | Reactivate User | Medium | Inactive user exists | POST /users/manage/{id}/reactivate/ | 200 OK, user active |
| TC-USER-007 | Create User (Admin) | Medium | Admin authenticated | POST /users/manage/ | 201 Created, auto-approved |
| TC-USER-008 | Filter by Approval Status | Medium | Users exist | GET /users/manage/?is_approved=false | 200 OK, pending users |
| TC-USER-009 | Filter by Role | Medium | Users exist | GET /users/manage/?role=manager | 200 OK, managers only |

---

## 3. Ticket Tests (TC-TICKET)

| ID | Test Case | Priority | Precondition | Steps | Expected Result |
|----|-----------|----------|--------------|-------|-----------------|
| TC-TICKET-001 | Create Ticket | High | Authenticated | POST /tickets/ with valid data | 201 Created, status=requested |
| TC-TICKET-002 | Create - Missing Title | High | Authenticated | POST /tickets/ without title | 400 Bad Request |
| TC-TICKET-003 | List Own Tickets | High | Member authenticated | GET /tickets/ | 200 OK, own tickets only |
| TC-TICKET-004 | List All Tickets (Manager) | High | Manager authenticated | GET /tickets/ | 200 OK, all tickets |
| TC-TICKET-005 | Get Ticket Detail | High | Ticket exists | GET /tickets/{id}/ | 200 OK, full details |
| TC-TICKET-006 | Update Ticket | Medium | Ticket exists | PATCH /tickets/{id}/ | 200 OK, updated |
| TC-TICKET-007 | Delete Ticket | Medium | Ticket exists | DELETE /tickets/{id}/ | 204 No Content |
| TC-TICKET-008 | Filter by Status | Medium | Tickets exist | GET /tickets/?status=in_progress | 200 OK, filtered |
| TC-TICKET-009 | Filter by Priority | Medium | Tickets exist | GET /tickets/?priority=urgent | 200 OK, filtered |
| TC-TICKET-010 | Search Tickets | Medium | Tickets exist | GET /tickets/?search=keyword | 200 OK, matching |
| TC-TICKET-011 | Date Range Filter | Low | Tickets exist | GET /tickets/?date_from=X&date_to=Y | 200 OK, in range |

---

## 4. Ticket Action Tests (TC-ACTION)

| ID | Test Case | Priority | Precondition | Steps | Expected Result |
|----|-----------|----------|--------------|-------|-----------------|
| TC-ACTION-001 | Approve Ticket | High | Requested ticket, Manager | POST /tickets/{id}/approve/ | 200 OK, status=approved |
| TC-ACTION-002 | Approve - Non-Manager | High | Member authenticated | POST /tickets/{id}/approve/ | 403 Forbidden |
| TC-ACTION-003 | Reject Ticket | High | Requested ticket, Manager | POST /tickets/{id}/reject/ with reason | 200 OK, status=rejected |
| TC-ACTION-004 | Assign Ticket | High | Approved ticket, Manager | POST /tickets/{id}/assign/ with user_id | 200 OK, assigned |
| TC-ACTION-005 | Assign - Not Approved | Medium | Requested ticket | Assign ticket | 400 Bad Request |
| TC-ACTION-006 | Start Work | High | Assigned ticket | POST /tickets/{id}/start/ | 200 OK, status=in_progress |
| TC-ACTION-007 | Start - Not Assigned | Medium | Unassigned ticket | Start work | 400 Bad Request |
| TC-ACTION-008 | Complete Ticket | High | In progress ticket | POST /tickets/{id}/complete/ | 200 OK, status=completed |
| TC-ACTION-009 | Confirm Completion | High | Completed ticket, Requester | POST /tickets/{id}/confirm/ | 200 OK, confirmed |
| TC-ACTION-010 | Confirm - Not Requester | Medium | Completed ticket | Confirm as non-requester | 403 Forbidden |

---

## 5. Comment Tests (TC-COMMENT)

| ID | Test Case | Priority | Precondition | Steps | Expected Result |
|----|-----------|----------|--------------|-------|-----------------|
| TC-COMMENT-001 | Add Comment | High | Ticket exists | POST /tickets/{id}/comments/ | 201 Created |
| TC-COMMENT-002 | Reply to Comment | Medium | Comment exists | POST with parent_id | 201 Created, nested |
| TC-COMMENT-003 | List Comments | Medium | Comments exist | GET /tickets/{id}/comments/ | 200 OK, with replies |

---

## 6. Attachment Tests (TC-ATTACH)

| ID | Test Case | Priority | Precondition | Steps | Expected Result |
|----|-----------|----------|--------------|-------|-----------------|
| TC-ATTACH-001 | Upload Attachment | High | Ticket exists | POST multipart/form-data | 201 Created |
| TC-ATTACH-002 | Delete Attachment | Medium | Own attachment | DELETE /attachments/{id}/ | 204 No Content |
| TC-ATTACH-003 | Delete - Not Owner | Medium | Other's attachment | Delete | 403 Forbidden |

---

## 7. Notification Tests (TC-NOTIF)

| ID | Test Case | Priority | Precondition | Steps | Expected Result |
|----|-----------|----------|--------------|-------|-----------------|
| TC-NOTIF-001 | List Notifications | Medium | Notifications exist | GET /notifications/ | 200 OK, user's notifications |
| TC-NOTIF-002 | Mark as Read | Medium | Unread notification | POST /notifications/{id}/read/ | 200 OK |
| TC-NOTIF-003 | Mark All Read | Medium | Multiple unread | POST /notifications/read_all/ | 200 OK |
| TC-NOTIF-004 | Unread Count | Medium | Notifications exist | GET /notifications/unread_count/ | 200 OK, count |

---

## 8. Activity Log Tests (TC-ACTIVITY)

| ID | Test Case | Priority | Precondition | Steps | Expected Result |
|----|-----------|----------|--------------|-------|-----------------|
| TC-ACTIVITY-001 | List Activities | Medium | Activities exist | GET /activities/ | 200 OK, activities |
| TC-ACTIVITY-002 | Activity on Action | Medium | Perform action | Perform ticket action | Activity logged |

---

## 9. Dashboard Tests (TC-DASH)

| ID | Test Case | Priority | Precondition | Steps | Expected Result |
|----|-----------|----------|--------------|-------|-----------------|
| TC-DASH-001 | Get Stats | High | Authenticated | GET /dashboard/stats/ | 200 OK, stats object |
| TC-DASH-002 | My Tasks | Medium | Authenticated | GET /dashboard/my-tasks/ | 200 OK, assigned tickets |
| TC-DASH-003 | Team Overview | Medium | Manager authenticated | GET /dashboard/team-overview/ | 200 OK |
| TC-DASH-004 | Overdue Tickets | Medium | Authenticated | GET /dashboard/overdue/ | 200 OK, overdue list |

---

## 10. E2E Tests

### Authentication Flow (E2E-AUTH)
| ID | Test Case | Priority |
|----|-----------|----------|
| E2E-AUTH-001 | Complete login flow with valid credentials | High |
| E2E-AUTH-002 | Login error display for invalid credentials | High |
| E2E-AUTH-003 | Registration flow with success message | High |
| E2E-AUTH-004 | Registration validation (password mismatch) | Medium |
| E2E-AUTH-005 | Logout clears session and redirects | High |
| E2E-AUTH-006 | Protected route redirects unauthenticated users | High |

### Ticket Workflow (E2E-TICKET)
| ID | Test Case | Priority |
|----|-----------|----------|
| E2E-TICKET-001 | Create ticket and verify in list | High |
| E2E-TICKET-002 | Search and filter tickets | Medium |
| E2E-TICKET-003 | View ticket details | High |
| E2E-TICKET-004 | Add comment to ticket | Medium |
| E2E-TICKET-005 | Reply to comment | Low |
| E2E-TICKET-006 | Upload attachment | Medium |
| E2E-TICKET-007 | Complete ticket workflow | High |

### User Management (E2E-USER)
| ID | Test Case | Priority |
|----|-----------|----------|
| E2E-USER-001 | Admin approves new user | High |
| E2E-USER-002 | Admin changes user role | Medium |
| E2E-USER-003 | Admin creates new user | Medium |
| E2E-USER-004 | Filter users by status | Low |
| E2E-USER-005 | Non-admin cannot access user management | High |

### Navigation (E2E-NAV)
| ID | Test Case | Priority |
|----|-----------|----------|
| E2E-NAV-001 | Dashboard loads with correct stats | High |
| E2E-NAV-002 | Navigation between all pages | High |
| E2E-NAV-003 | Notification badge updates | Medium |
| E2E-NAV-004 | Activity log displays actions | Medium |
| E2E-NAV-005 | Quick actions navigate correctly | Medium |

---

## Test Statistics

| Category | Total Tests | High Priority | Medium Priority | Low Priority |
|----------|-------------|---------------|-----------------|--------------|
| TC-AUTH | 12 | 8 | 4 | 0 |
| TC-USER | 9 | 5 | 4 | 0 |
| TC-TICKET | 11 | 5 | 5 | 1 |
| TC-ACTION | 10 | 6 | 4 | 0 |
| TC-COMMENT | 3 | 1 | 2 | 0 |
| TC-ATTACH | 3 | 1 | 2 | 0 |
| TC-NOTIF | 4 | 0 | 4 | 0 |
| TC-ACTIVITY | 2 | 0 | 2 | 0 |
| TC-DASH | 4 | 1 | 3 | 0 |
| E2E | 19 | 10 | 7 | 2 |
| **Total** | **77** | **37** | **37** | **3** |

# User Management – Create & Delete Test Cases

Test cases for the **Create User** and **Delete User** features.  
Use this checklist before running in production.

---

## Prerequisites

- [ ] Logged in as **admin** (only admin can create/delete users)
- [ ] User Management page: `/user-management`
- [ ] API base: `POST /api/users`, `DELETE /api/users/<username>`

---

## 1. CREATE USER – Test Cases

### TC-CREATE-01: Create user – success (happy path)

| Field | Value |
|-------|--------|
| **ID** | TC-CREATE-01 |
| **Description** | Create a new user with all valid data |
| **Preconditions** | Logged in as admin |

**Steps:**

1. Open User Management → click **Add New User**
2. Fill in:
   - Username: `testuser001`
   - Password: `password8` (≥8 chars)
   - First name: `Test`
   - Last name: `User`
   - Role: **Site Admin** (or Doctor)
   - Position: **Site Administrator** (or GP)
   - Location: check at least one (e.g. **All** or **Parafield Gardens**)
3. Click **Save**

**Expected:**

- [ ] Toast (top-right, green): `User 'testuser001' created successfully`
- [ ] Modal closes
- [ ] New user appears in the table
- [ ] No error in browser console

**Result:** x Pass ☐ Fail

---

### TC-CREATE-02: Username uniqueness – duplicate rejected

| Field | Value |
|-------|--------|
| **ID** | TC-CREATE-02 |
| **Description** | Creating a user with an existing username must fail |
| **Preconditions** | Logged in as admin; user `admin` (or any existing user) already exists |

**Steps:**

1. Add New User
2. Set Username: `admin` (or another existing username)
3. Set Password: `password123`, other fields valid
4. Click **Save**

**Expected:**

- [ ] Toast (top-right, red): `User 'admin' already exists` (or similar)
- [ ] Modal stays open
- [ ] User list unchanged
- [ ] API returns `400` with message about user already existing

**Result:** x Pass ☐ Fail

---

### TC-CREATE-03: Username uniqueness – case-insensitive

| Field | Value |
|-------|--------|
| **ID** | TC-CREATE-03 |
| **Description** | Duplicate check is case-insensitive (e.g. `Admin` vs `admin`) |
| **Preconditions** | User `admin` exists |

**Steps:**

1. Add New User
2. Set Username: `Admin` (different case)
3. Fill other required fields validly, click **Save**

**Expected:**

- [ ] Toast (red): `User 'Admin' already exists` or equivalent
- [ ] User is **not** created

**Result:** x Pass ☐ Fail

---

### TC-CREATE-04: Password – too short (< 8 characters)

| Field | Value |
|-------|--------|
| **ID** | TC-CREATE-04 |
| **Description** | Password must be at least 8 characters |

**Steps:**

1. Add New User
2. Set Password: `short`
3. Fill other required fields, click **Save**

**Expected:**

- [ ] Toast (red): `Password must be at least 8 characters long`
- [ ] Modal stays open, user not created
- [ ] Same behavior if password is empty

**Result:** x Pass ☐ Fail

---

### TC-CREATE-05: Password – exactly 8 characters accepted

| Field | Value |
|-------|--------|
| **ID** | TC-CREATE-05 |
| **Description** | Password with exactly 8 characters is accepted |

**Steps:**

1. Add New User
2. Username: `testuser008`, Password: `12345678`
3. Fill other required fields, click **Save**

**Expected:**

- [ ] Toast (green): `User 'testuser008' created successfully`
- [ ] User appears in list

**Result:** x Pass ☐ Fail

---

### TC-CREATE-06: Admin role – cannot create admin user

| Field | Value |
|-------|--------|
| **ID** | TC-CREATE-06 |
| **Description** | New users cannot have role "admin" |

**Steps:**

1. Add New User
2. Set Role: **Admin** (if that option exists in UI)
3. Or send API request with `"role": "admin"` in body
4. Submit

**Expected:**

- [ ] Toast (red): `Cannot create admin users. Only one admin account exists in the system.`
- [ ] User with role admin is **not** created

**Result:** x Pass ☐ Fail

---

### TC-CREATE-07: Required fields – missing username

| Field | Value |
|-------|--------|
| **ID** | TC-CREATE-07 |
| **Description** | Username is required |

**Steps:**

1. Add New User
2. Leave Username empty (or only spaces)
3. Fill other fields, click **Save**

**Expected:**

- [ ] Toast (red): `Username is required` or `Username cannot be empty`
- [ ] User not created

**Result:** x Pass ☐ Fail

---

### TC-CREATE-08: Required fields – missing first/last name

| Field | Value |
|-------|--------|
| **ID** | TC-CREATE-08 |
| **Description** | First name and last name are required |

**Steps:**

1. Add New User
2. Leave First name or Last name empty
3. Fill other required fields, click **Save**

**Expected:**

- [ ] Toast (red): `First name is required` or `Last name is required` (or equivalent)
- [ ] User not created

**Result:** x Pass ☐ Fail

---

### TC-CREATE-09: Required fields – no location

| Field | Value |
|-------|--------|
| **ID** | TC-CREATE-09 |
| **Description** | At least one location must be selected |

**Steps:**

1. Add New User
2. Leave all Location checkboxes unchecked
3. Fill other required fields, click **Save**

**Expected:**

- [ ] Toast (red): `Please select at least one location` or similar
- [ ] User not created

**Result:** x Pass ☐ Fail

---

### TC-CREATE-10: Non-admin – cannot create user

| Field | Value |
|-------|--------|
| **ID** | TC-CREATE-10 |
| **Description** | Only admin can create users |

**Steps:**

1. Log in as **non-admin** (e.g. site_admin or doctor)
2. Open User Management (if allowed) and try Add New User,  
   OR send `POST /api/users` with valid JSON body

**Expected:**

- [ ] API returns `403` with message like `Access denied`
- [ ] If UI allows access, create action still fails with access denied
- [ ] No new user in system

**Result:** x Pass ☐ Fail

---

### TC-CREATE-11: Toast – success shown top-right

| Field | Value |
|-------|--------|
| **ID** | TC-CREATE-11 |
| **Description** | Success message appears as toast, top-right |

**Steps:**

1. As admin, create a user successfully (e.g. TC-CREATE-01)

**Expected:**

- [ ] Green toast appears in **top-right**
- [ ] Message is the success text (e.g. `User '...' created successfully`)
- [ ] Toast auto-disappears after a few seconds or can be closed with ×

**Result:** x Pass ☐ Fail

---

### TC-CREATE-12: Toast – error shown top-right

| Field | Value |
|-------|--------|
| **ID** | TC-CREATE-12 |
| **Description** | Error messages appear as toast, top-right |

**Steps:**

1. Trigger any validation error (e.g. short password, duplicate username)

**Expected:**

- [ ] Red toast appears in **top-right**
- [ ] Message matches the validation/API error
- [ ] Toast can be dismissed or auto-closes

**Result:** x Pass ☐ Fail

---

## 2. DELETE USER – Test Cases

### TC-DELETE-01: Delete user – success (happy path)

| Field | Value |
|-------|--------|
| **ID** | TC-DELETE-01 |
| **Description** | Delete a non-admin user as admin |
| **Preconditions** | Logged in as admin; at least one non-admin user exists (e.g. from TC-CREATE-01) |

**Steps:**

1. On User Management, find a user that is **not** the current admin
2. Click **Delete** (🗑️)
3. In dialog: “Are you sure you want to delete user …?” → click **Delete** (or Confirm)

**Expected:**

- [ ] Confirmation dialog appears with correct username
- [ ] After confirm: toast (green) e.g. `User '...' deleted successfully`
- [ ] User disappears from table
- [ ] API returns `200` with `success: true`

**Result:** x Pass ☐ Fail

---

### TC-DELETE-02: Delete – confirmation dialog shown

| Field | Value |
|-------|--------|
| **ID** | TC-DELETE-02 |
| **Description** | Delete action shows “Are you sure?” before calling API |

**Steps:**

1. Click **Delete** on any user

**Expected:**

- [ ] Dialog/modal appears
- [ ] Text includes “Are you sure you want to delete user **&lt;username&gt;**?”
- [ ] Buttons: Cancel and Delete (or Yes/No)
- [ ] No delete request sent until user confirms

**Result:** x Pass ☐ Fail

---

### TC-DELETE-03: Delete – cancel does not delete

| Field | Value |
|-------|--------|
| **ID** | TC-DELETE-03 |
| **Description** | Cancel closes dialog and does not delete |

**Steps:**

1. Click **Delete** on a user
2. In dialog, click **Cancel** (or X / outside)

**Expected:**

- [ ] Dialog closes
- [ ] No DELETE request sent (check Network tab)
- [ ] User still in list

**Result:** x Pass ☐ Fail

---

### TC-DELETE-04: Self-deletion – cannot delete own account

| Field | Value |
|-------|--------|
| **ID** | TC-DELETE-04 |
| **Description** | Admin cannot delete their own account |

**Steps:**

1. Log in as **admin**
2. Click **Delete** on the **admin** user
3. In confirmation dialog, click **Delete**

**Expected:**

- [ ] API returns `400` (or appropriate error code)
- [ ] Toast (red): `Cannot delete your own account`
- [ ] Admin user still in list

**Result:** x Pass ☐ Fail

---

### TC-DELETE-05: Non-admin – cannot delete user

| Field | Value |
|-------|--------|
| **ID** | TC-DELETE-05 |
| **Description** | Only admin can delete users |

**Steps:**

1. Log in as **non-admin** (e.g. site_admin or doctor)
2. If UI shows Delete, click it; or send `DELETE /api/users/<some_username>`

**Expected:**

- [ ] API returns `403` with message like `Access denied`
- [ ] No user is deleted

**Result:** x Pass ☐ Fail

---

### TC-DELETE-06: Delete non-existent user

| Field | Value |
|-------|--------|
| **ID** | TC-DELETE-06 |
| **Description** | Deleting unknown username returns clear error |

**Steps:**

1. As admin, send: `DELETE /api/users/nonexistentuser999`
2. (Or use a UI path that allows targeting that user, if any)

**Expected:**

- [ ] API returns `400` (or `404`) with message like `User 'nonexistentuser999' not found`
- [ ] Toast (red) shows same or similar message

**Result:** x Pass ☐ Fail

---

### TC-DELETE-07: Toast – delete success top-right

| Field | Value |
|-------|--------|
| **ID** | TC-DELETE-07 |
| **Description** | Delete success appears as green toast, top-right |

**Steps:**

1. Successfully delete a user (e.g. TC-DELETE-01)

**Expected:**

- [ ] Green toast in **top-right**
- [ ] Message like `User '...' deleted successfully`

**Result:** x Pass ☐ Fail

---

### TC-DELETE-08: Toast – delete error top-right

| Field | Value |
|-------|--------|
| **ID** | TC-DELETE-08 |
| **Description** | Delete errors (e.g. self-delete, 403) show as red toast, top-right |

**Steps:**

1. Trigger a delete error (e.g. try to delete own account, or call API as non-admin)

**Expected:**

- [ ] Red toast in **top-right**
- [ ] Message matches the error (e.g. `Cannot delete your own account` or `Access denied`)

**Result:** x Pass ☐ Fail

---

## 3. API Quick Reference

Use these to run manual API tests (e.g. with curl or Postman).

**Create user (admin only):**

```http
POST /api/users
Content-Type: application/json
Cookie: session=... (admin session)

{
  "username": "newuser",
  "password": "password8",
  "first_name": "First",
  "last_name": "Last",
  "role": "site_admin",
  "position": "Site Administrator",
  "location": ["All"],
  "landing_page": null
}
```

**Delete user (admin only):**

```http
DELETE /api/users/<username>
Cookie: session=... (admin session)
```

**Valid roles (create only):**  
`site_admin`, `doctor`, `physiotherapist`, `nurse`, `registered_nurse`, `carer`, `clinical_manager`  
**Invalid for new users:** `admin`

---

## 4. Test Run Summary

| Date | Tester | Create passed | Create failed | Delete passed | Delete failed | Notes |
|------|--------|----------------|---------------|----------------|---------------|-------|
|      |        | /12            |               | /8             |               |       |
|      |        |                |               |                |               |       |

---

## 5. Sign-off Before Release

- [ ] All Create test cases executed and passed (or known failures documented)
- [ ] All Delete test cases executed and passed (or known failures documented)
- [ ] Toasts (success/error) appear top-right as specified
- [ ] No critical bugs open for Create/Delete

**Approved by:** ______minh quoc vo_________________ **Date:** _27/01/2026__________

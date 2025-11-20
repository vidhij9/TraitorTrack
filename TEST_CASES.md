# TraitorTrack - Comprehensive Test Cases

**For:** Customer Care & QA Team  
**Purpose:** Test every feature of TraitorTrack thoroughly  
**Date:** November 20, 2025  
**Version:** 2.0

---

## ⚠️ CRITICAL SECURITY WARNING ⚠️

### 🚨 USE DEVELOPMENT ENVIRONMENT ONLY! 🚨

**BEFORE TESTING, READ THIS:**

1. ❌ **NEVER test on production** (https://traitor-track.replit.app)
2. ✅ **ONLY test on development/staging** environment
3. ❌ **NEVER use real admin credentials** (admin/superadmin)
4. ✅ **Request test accounts** from system administrator
5. ❌ **NEVER delete production data** - it has 344,683+ real bags!

**Production environment contains real customer data that must NEVER be modified during testing.**

See "Testing Environment Setup" section below for detailed instructions.

---

## 📋 Table of Contents

1. [How to Use This Document](#how-to-use-this-document)
2. [Test Account Credentials](#test-account-credentials)
3. [Section 1: Login & User Management](#section-1-login--user-management)
4. [Section 2: Dashboard & Statistics](#section-2-dashboard--statistics)
5. [Section 3: Bag Management](#section-3-bag-management)
6. [Section 4: Scanning Operations](#section-4-scanning-operations)
7. [Section 5: Bill Management](#section-5-bill-management)
8. [Section 6: Search & Filtering](#section-6-search--filtering)
9. [Section 7: Reports & Data Export](#section-7-reports--data-export)
10. [Section 8: Admin Features](#section-8-admin-features)
11. [Section 9: Security Features](#section-9-security-features)
12. [Section 10: Mobile Testing](#section-10-mobile-testing)
13. [Section 11: Load Testing](#section-11-load-testing)
14. [Section 12: Error Handling](#section-12-error-handling)

---

## How to Use This Document

### Test Case Format
Each test case has:
- **Test ID:** Unique number (e.g., TC-001)
- **Test Name:** What you're testing
- **Steps:** What to do (numbered steps)
- **Expected Result:** What should happen
- **Type:** POSITIVE (should work) or NEGATIVE (should fail safely)

### Testing Symbols
- ✅ = Test Passed
- ❌ = Test Failed
- ⚠️ = Partial Pass (note the issue)
- 📝 = Notes (write down observations)

### How to Test
1. **VERIFY YOU'RE ON DEVELOPMENT** - Check URL is NOT production!
2. Start from the top and work your way down
3. Mark each test as ✅, ❌, or ⚠️ 
4. Write notes for any failures
5. Test on different devices (computer, phone, tablet)
6. Try to break things! The system should handle errors gracefully

### 🚨 CRITICAL: Apply These Rules to ALL Test Cases Below

**For EVERY test case in this document:**
1. Replace "admin" with "test_admin" (development test account)
2. Replace "superadmin" with "test_admin" (development test account)
3. Replace "biller" with "test_biller" (development test account)
4. Replace "dispatcher" with "test_dispatcher" (development test account)
5. Assume you're on DEVELOPMENT environment, NOT production
6. Use test QR codes (not real production bag numbers)
7. NEVER perform destructive actions on production

**If a test step says "Login as admin" → interpret as "Login as test_admin on DEVELOPMENT"**  
**If a test step says "Login as biller" → interpret as "Login as test_biller on DEVELOPMENT"**  
**If a test step says "Login as dispatcher" → interpret as "Login as test_dispatcher on DEVELOPMENT"**

---

## ⚠️ CRITICAL: Testing Environment Setup

### 🚨 DO NOT TEST ON PRODUCTION! 🚨

**NEVER run these tests on the production website!**  
Production contains real customer data (344,683+ bags) that must not be modified or deleted.

### Testing Environment Options

#### Option 1: Development/Staging Environment (RECOMMENDED)
- **URL:** https://traitor-track-dev.replit.app (or your staging URL)
- **Database:** Replit PostgreSQL (development database)
- **Purpose:** Safe testing environment with sample data
- **Data Reset:** Can be reset anytime without affecting production

#### Option 2: Local Development Setup
- **URL:** http://localhost:5000
- **Database:** Local Replit PostgreSQL
- **Purpose:** Developer testing on their own machine
- **Data Reset:** Fresh database on each restart

### How to Set Up Test Environment

**Step 1: Ask Admin to Create Test Accounts**
Contact your system administrator to create test accounts in the DEVELOPMENT environment:

```
Admin Test Account:
- Username: test_admin
- Password: [Admin will provide]
- Role: Administrator
- Environment: DEVELOPMENT ONLY

Biller Test Account:
- Username: test_biller
- Password: [Admin will provide]
- Role: Biller
- Environment: DEVELOPMENT ONLY

Dispatcher Test Account:
- Username: test_dispatcher
- Password: [Admin will provide]
- Role: Dispatcher
- Dispatch Area: Lucknow
- Environment: DEVELOPMENT ONLY
```

**Step 2: Verify You're on Development**
Before testing, verify:
1. ✅ URL is NOT https://traitor-track.replit.app (production)
2. ✅ URL is the staging/dev environment
3. ✅ Database has sample/test data only
4. ✅ Test accounts work

**Step 3: Reset Test Data (Before Each Test Cycle)**
Ask admin to:
1. Reset development database to clean state
2. Load sample bags for testing (100-1000 bags)
3. Verify all test accounts are active

### Test Data Guidelines

**Safe to Test:**
- ✅ Development/Staging environment only
- ✅ Test accounts with "test_" prefix
- ✅ Sample data that can be deleted
- ✅ All destructive tests (delete, unlink, etc.)

**NEVER Test On:**
- ❌ Production URL (https://traitor-track.replit.app)
- ❌ Real admin accounts (admin, superadmin)
- ❌ Real customer data
- ❌ Production database

### Test Account Credentials

**FOR DEVELOPMENT/STAGING ENVIRONMENT ONLY:**

#### Admin Test Account
- **Username:** test_admin
- **Password:** [Request from admin - DO NOT SHARE]
- **Role:** Administrator
- **Can do:** Everything (in dev environment)

#### Biller Test Account
- **Username:** test_biller
- **Password:** [Request from admin - DO NOT SHARE]
- **Role:** Biller
- **Can do:** Create bills, scan bags, view all areas

#### Dispatcher Test Account
- **Username:** test_dispatcher
- **Password:** [Request from admin - DO NOT SHARE]
- **Role:** Dispatcher
- **Dispatch Area:** Lucknow
- **Can do:** Scan bags in Lucknow area only

### Production Access (View-Only Testing)

If you MUST verify production (read-only checks only):
- **URL:** https://traitor-track.replit.app
- **Login:** [Contact admin for temporary read-only credentials]
- **Allowed Actions:**
  - ✅ View dashboard statistics
  - ✅ View bag lists
  - ✅ View bill lists
  - ✅ Search functionality
  - ✅ Report viewing
- **NEVER DO:**
  - ❌ Create/delete bags
  - ❌ Create/delete bills
  - ❌ Modify any data
  - ❌ Delete users
  - ❌ Test error scenarios
  - ❌ Run destructive tests

---

## Section 1: Login & User Management

**⚠️ REMINDER: All tests in this section MUST be run on DEVELOPMENT environment ONLY!**  
**Use test_admin, test_biller, test_dispatcher accounts - NEVER use production admin accounts!**

---

### TC-001: Admin Login (POSITIVE)
**Steps:**
1. Open the DEVELOPMENT website (verify URL is NOT production!)
2. Click on "Login" or go to /login
3. Enter username: `test_admin`
4. Enter password: [Use password provided by admin for test_admin account]
5. Click "Login" button

**Expected Result:**
- ✅ Page loads successfully
- ✅ No error messages
- ✅ Redirected to Dashboard page
- ✅ You see "Welcome, test_admin" or similar greeting
- ✅ Navigation menu shows admin options

**Type:** POSITIVE  
**Priority:** CRITICAL

---

### TC-002: Login with Wrong Password (NEGATIVE)
**Steps:**
1. Go to DEVELOPMENT login page
2. Enter username: `test_admin`
3. Enter password: `wrongpassword123`
4. Click "Login" button

**Expected Result:**
- ✅ Login fails
- ✅ Error message: "Invalid username or password"
- ✅ Stay on login page
- ✅ No access to dashboard
- ✅ Password field cleared for security

**Type:** NEGATIVE  
**Priority:** HIGH

---

### TC-003: Login with Non-Existent User (NEGATIVE)
**Steps:**
1. Go to login page
2. Enter username: `fakeuser999`
3. Enter password: `anything123`
4. Click "Login" button

**Expected Result:**
- ✅ Login fails
- ✅ Same error message as wrong password (security: don't reveal which usernames exist)
- ✅ Stay on login page

**Type:** NEGATIVE  
**Priority:** HIGH

---

### TC-004: Account Lockout After Failed Attempts (NEGATIVE)
**Steps:**
1. Go to DEVELOPMENT login page
2. Try to login with username `test_admin` and wrong password
3. Repeat this 5 times (or however many attempts trigger lockout)
4. Watch what happens

**Expected Result:**
- ✅ After 5 failed attempts, account gets locked
- ✅ Error message: "Account locked for 15 minutes"
- ✅ Can't login even with correct password during lockout
- ✅ After 15 minutes, can login again
- ✅ (Note: Ask admin to unlock test account if needed before 15 min)

**Type:** NEGATIVE (Security Feature)  
**Priority:** HIGH

---

### TC-005: Logout Successfully (POSITIVE)
**Steps:**
1. Login as test_admin on DEVELOPMENT
2. Click "Logout" button or link
3. Observe what happens

**Expected Result:**
- ✅ Logged out successfully
- ✅ Redirected to login page
- ✅ Message: "Logged out successfully" or similar
- ✅ Can't access dashboard by typing /dashboard in browser
- ✅ Session cleared

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-006: Session Timeout After Inactivity (POSITIVE)
**Steps:**
1. Login as test_admin on DEVELOPMENT
2. Don't touch anything for 1 hour
3. Try to click something after 1 hour

**Expected Result:**
- ✅ Session expires after 1 hour
- ✅ Redirected to login page
- ✅ Message: "Session expired, please login again"
- ✅ Must login again to continue

**Type:** POSITIVE (Security Feature)  
**Priority:** MEDIUM

---

### TC-007: Two-Factor Authentication Setup (Admin Only) (POSITIVE)
**Steps:**
1. Login as test_admin on DEVELOPMENT
2. Go to Settings or Profile page
3. Find "Enable Two-Factor Authentication" option
4. Click "Setup 2FA"
5. Scan QR code with Google Authenticator or similar app
6. Enter the 6-digit code from app
7. Click "Enable"

**Expected Result:**
- ✅ QR code displays properly
- ✅ After entering correct code, 2FA is enabled
- ✅ Message: "Two-factor authentication enabled"
- ✅ Next login will require 6-digit code
- ✅ Backup codes provided (save these!)

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-008: Login with 2FA Enabled (POSITIVE)
**Steps:**
1. After enabling 2FA (TC-007)
2. Logout
3. Login with username and password
4. System asks for 6-digit code
5. Open authenticator app, get code
6. Enter code and submit

**Expected Result:**
- ✅ After password, prompted for 2FA code
- ✅ Code from app works
- ✅ Successfully logged in
- ✅ If code is wrong, shows error and tries again

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-009: Create New User (Admin Only) (POSITIVE)
**Steps:**
1. Login as test_admin on DEVELOPMENT
2. Go to "User Management" page
3. Click "Create New User" button
4. Fill in:
   - Username: `devuser1`
   - Email: `devuser1@example.com`
   - Password: `DevTest@1234`
   - Role: Dispatcher
   - Dispatch Area: Lucknow
5. Click "Create User"

**Expected Result:**
- ✅ User created successfully
- ✅ Message: "User created successfully"
- ✅ New user appears in user list
- ✅ Can login with devuser1/DevTest@1234
- ✅ New user can only access Lucknow dispatch area

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-010: Create User with Duplicate Username (NEGATIVE)
**Steps:**
1. Login as test_admin on DEVELOPMENT
2. Go to "User Management"
3. Try to create user with username: `test_admin` (already exists)
4. Fill other fields
5. Click "Create User"

**Expected Result:**
- ✅ Creation fails
- ✅ Error message: "Username already exists"
- ✅ Stay on form page
- ✅ No duplicate user created

**Type:** NEGATIVE  
**Priority:** MEDIUM

---

### TC-011: Create User with Weak Password (NEGATIVE)
**Steps:**
1. Login as test_admin on DEVELOPMENT
2. Go to "User Management"
3. Try to create user with password: `123` (too short)
4. Fill other fields
5. Click "Create User"

**Expected Result:**
- ✅ Creation fails
- ✅ Error message: "Password must be at least 8 characters"
- ✅ Form shows validation error
- ✅ User not created

**Type:** NEGATIVE  
**Priority:** MEDIUM

---

### TC-012: Edit User Details (Admin Only) (POSITIVE)
**Steps:**
1. Login as test_admin on DEVELOPMENT
2. Go to "User Management"
3. Find devuser1 (created in TC-009)
4. Click "Edit" button
5. Change dispatch area to "Indore"
6. Click "Save Changes"

**Expected Result:**
- ✅ Changes saved successfully
- ✅ Message: "User updated successfully"
- ✅ User list shows updated dispatch area
- ✅ User can now access Indore area

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-013: Delete User (Admin Only) (POSITIVE)
**Steps:**
1. Login as test_admin on DEVELOPMENT
2. Go to "User Management"
3. Find devuser1 (test user created earlier)
4. Click "Delete" button
5. Confirm deletion when asked

**Expected Result:**
- ✅ Confirmation popup appears: "Are you sure?"
- ✅ After confirming, user deleted
- ✅ Message: "User deleted successfully"
- ✅ User removed from list
- ✅ Can't login with deleted credentials
- ✅ User's scan history preserved (not deleted)

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-014: Reset Password for User (Admin Only) (POSITIVE)
**Steps:**
1. Login as test_admin on DEVELOPMENT
2. Go to "User Management"
3. Find test_biller or test_dispatcher
4. Click "Reset Password" button
5. Enter new password: `NewPass@2024`
6. Confirm new password
7. Click "Reset"

**Expected Result:**
- ✅ Password reset successfully
- ✅ Message: "Password reset successfully"
- ✅ User can login with new password
- ✅ Old password no longer works
- ✅ Admin sees confirmation

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-015: Forgot Password Flow (POSITIVE)
**Steps:**
1. Go to login page
2. Click "Forgot Password?" link
3. Enter email address
4. Click "Send Reset Link"
5. Check email inbox
6. Click reset link in email
7. Enter new password
8. Submit

**Expected Result:**
- ✅ Email sent message appears
- ✅ Email received within 5 minutes
- ✅ Reset link works
- ✅ Can set new password
- ✅ Can login with new password
- ✅ Reset link expires after 1 hour

**Type:** POSITIVE  
**Priority:** HIGH

---

## Section 2: Dashboard & Statistics

**⚠️ REMINDER: All tests in this section MUST be run on DEVELOPMENT environment ONLY!**

---

### TC-016: View Dashboard as Admin (POSITIVE)
**Steps:**
1. Login as admin
2. Dashboard loads automatically OR click "Dashboard" link

**Expected Result:**
- ✅ Dashboard loads quickly (under 2 seconds)
- ✅ Shows total bags count
- ✅ Shows parent bags count
- ✅ Shows child bags count
- ✅ Shows total bills count
- ✅ Shows total users count
- ✅ Shows recent activity
- ✅ All numbers are accurate
- ✅ No loading errors

**Type:** POSITIVE  
**Priority:** CRITICAL

---

### TC-017: Dashboard Auto-Refresh (POSITIVE)
**Steps:**
1. Login and view dashboard
2. Keep dashboard open
3. In another browser tab, create a new bag
4. Wait 30 seconds
5. Look at dashboard (don't refresh manually)

**Expected Result:**
- ✅ Dashboard updates automatically (AJAX refresh)
- ✅ New bag count reflects the addition
- ✅ Recent activity shows the new bag
- ✅ No need to manually refresh page

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-018: View Dashboard Statistics (POSITIVE)
**Steps:**
1. Login as any role
2. View dashboard
3. Check all statistics cards

**Expected Result:**
- ✅ Total Bags shows correct count
- ✅ Parent Bags shows correct count (bags with type=parent)
- ✅ Child Bags shows correct count (bags with type=child)
- ✅ Active Bills shows correct count (bills not finished)
- ✅ Completed Bills shows correct count
- ✅ Today's Scans shows scans from today
- ✅ All numbers match database

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-019: Dashboard Performance Test (POSITIVE)
**Steps:**
1. Login
2. Measure time from clicking "Dashboard" to full page load
3. Use browser dev tools (F12) Network tab to check

**Expected Result:**
- ✅ Page loads in under 2 seconds
- ✅ Statistics load in under 500ms
- ✅ No JavaScript errors in console
- ✅ All data displays properly

**Type:** POSITIVE (Performance)  
**Priority:** HIGH

---

## Section 3: Bag Management

**⚠️ REMINDER: All tests in this section MUST be run on DEVELOPMENT environment ONLY!**  
**NEVER create/delete bags on production!**

---

### TC-020: View All Bags (POSITIVE)
**Steps:**
1. Login as any role
2. Click "Bag Management" or "View Bags"
3. View the bags list

**Expected Result:**
- ✅ Page loads successfully
- ✅ Shows list of all bags
- ✅ Each bag shows: QR ID, Type, Created Date
- ✅ Pagination works (if more than 50 bags)
- ✅ Can see both parent and child bags

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-021: Create Parent Bag - Mustard Format (POSITIVE)
**Steps:**
1. Login as admin or biller
2. Go to "Bag Management"
3. Click "Create Bag" or similar
4. Enter QR ID: `SB12345`
5. Select Type: Parent
6. Click "Create"

**Expected Result:**
- ✅ Bag created successfully
- ✅ Message: "Bag created successfully"
- ✅ Bag appears in list with QR ID: SB12345
- ✅ Type shows as "Parent"
- ✅ Can search for this bag by QR ID

**Type:** POSITIVE  
**Priority:** CRITICAL

---

### TC-022: Create Parent Bag - Moong Format (POSITIVE)
**Steps:**
1. Login as admin or biller
2. Go to "Bag Management"
3. Create new bag
4. Enter QR ID: `M444-67890`
5. Select Type: Parent
6. Click "Create"

**Expected Result:**
- ✅ Bag created successfully
- ✅ System accepts M444-##### format
- ✅ Bag appears in list
- ✅ Type shows as "Parent"

**Type:** POSITIVE  
**Priority:** CRITICAL

---

### TC-023: Create Child Bag (POSITIVE)
**Steps:**
1. Login as any role
2. Go to "Bag Management"
3. Create new bag
4. Enter QR ID: `CH123456`
5. Select Type: Child
6. Click "Create"

**Expected Result:**
- ✅ Bag created successfully
- ✅ Type shows as "Child"
- ✅ Child bag not linked to any parent yet
- ✅ Available to link later

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-024: Create Duplicate Bag (NEGATIVE)
**Steps:**
1. Create a bag with QR ID: `SB99999`
2. Try to create another bag with same QR ID: `SB99999`
3. Submit

**Expected Result:**
- ✅ Creation fails
- ✅ Error message: "Bag with this QR ID already exists"
- ✅ Stay on form
- ✅ No duplicate created

**Type:** NEGATIVE  
**Priority:** HIGH

---

### TC-025: Create Bag with Invalid QR Format (NEGATIVE)
**Steps:**
1. Try to create bag with QR ID: `INVALID123!@#`
2. Submit

**Expected Result:**
- ✅ Creation fails or shows warning
- ✅ Error: "Invalid QR ID format"
- ✅ System expects SB##### or M444-##### for parent bags
- ✅ No bag created with invalid format

**Type:** NEGATIVE  
**Priority:** MEDIUM

---

### TC-026: View Bag Details (POSITIVE)
**Steps:**
1. Login
2. Go to "Bag Management"
3. Click on any bag from the list
4. View bag details page

**Expected Result:**
- ✅ Details page loads
- ✅ Shows QR ID
- ✅ Shows Type (Parent/Child)
- ✅ Shows Created Date and Time
- ✅ Shows Created By (username)
- ✅ If parent: shows linked child bags
- ✅ If child: shows linked parent bag (if any)
- ✅ Shows scan history

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-027: Delete Bag (Admin Only) (POSITIVE)
**Steps:**
1. Login as admin
2. Go to "Bag Management"
3. Find a test bag (not important data)
4. Click "Delete" button
5. Confirm deletion

**Expected Result:**
- ✅ Confirmation popup: "Are you sure?"
- ✅ After confirm, bag deleted
- ✅ Message: "Bag deleted successfully"
- ✅ Bag removed from list
- ✅ Can't find bag by searching QR ID
- ✅ Scan history preserved

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-028: Link Child to Parent Bag (POSITIVE)
**Steps:**
1. Create a parent bag: `SB11111`
2. Create a child bag: `CH22222`
3. Go to scanning page or linking page
4. Scan/Enter parent QR: `SB11111`
5. Scan/Enter child QR: `CH22222`
6. Confirm link

**Expected Result:**
- ✅ Link created successfully
- ✅ Message: "Child bag linked to parent"
- ✅ View parent bag details - shows CH22222 as child
- ✅ View child bag details - shows SB11111 as parent
- ✅ Link visible in database

**Type:** POSITIVE  
**Priority:** CRITICAL

---

### TC-029: Unlink Child from Parent (POSITIVE)
**Steps:**
1. Find a child bag linked to parent (from TC-028)
2. Go to parent bag details or scanning page
3. Click "Unlink" button next to child bag
4. Confirm unlink

**Expected Result:**
- ✅ Confirmation: "Are you sure you want to unlink?"
- ✅ After confirm, child unlinked
- ✅ Message: "Child bag unlinked successfully"
- ✅ Parent no longer shows this child
- ✅ Child shows as unlinked
- ✅ Both bags still exist, just not linked

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-030: Link Same Child to Multiple Parents (NEGATIVE)
**Steps:**
1. Create parent1: `SB11111`
2. Create parent2: `SB22222`
3. Create child: `CH33333`
4. Link child to parent1 successfully
5. Try to link same child to parent2

**Expected Result:**
- ✅ Second link fails
- ✅ Error: "Child bag already linked to another parent"
- ✅ Child remains linked to parent1 only
- ✅ No double linking allowed

**Type:** NEGATIVE (Business Rule)  
**Priority:** HIGH

---

## Section 4: Scanning Operations

**⚠️ REMINDER: All tests in this section MUST be run on DEVELOPMENT environment ONLY!**  
**Use test QR codes and sample bags - NEVER scan production bags!**

---

### TC-031: Scan Parent Bag with Scanner Device (POSITIVE)
**Steps:**
1. Login on mobile device or scanner tablet
2. Go to "Scan Parent Bags" page
3. Use physical barcode scanner to scan QR code on bag
4. Scanner device reads QR: `SB55555`
5. System processes scan

**Expected Result:**
- ✅ Scanner input automatically captured
- ✅ QR ID appears in input field: SB55555
- ✅ System validates QR format
- ✅ If bag exists: shows bag details
- ✅ If bag doesn't exist: creates new parent bag
- ✅ Audio feedback (beep) on successful scan
- ✅ Visual feedback (green flash or checkmark)
- ✅ Input field clears for next scan

**Type:** POSITIVE  
**Priority:** CRITICAL

---

### TC-032: Scan Child Bag and Link to Parent (POSITIVE)
**Steps:**
1. Login
2. Go to "Scan Child Bags" page
3. First, scan parent bag: `SB12345`
4. Then scan child bag: `CH67890`
5. System processes both scans

**Expected Result:**
- ✅ After parent scan: shows "Parent bag selected: SB12345"
- ✅ After child scan: automatic linking happens
- ✅ Message: "Child CH67890 linked to parent SB12345"
- ✅ Audio/visual success feedback
- ✅ Ready for next child scan
- ✅ Can scan multiple children to same parent
- ✅ Link saved in database

**Type:** POSITIVE  
**Priority:** CRITICAL

---

### TC-033: Rapid Scanning - Multiple Children (POSITIVE)
**Steps:**
1. Go to child scanning page
2. Scan parent: `SB10000`
3. Quickly scan 10 children one after another:
   - CH10001, CH10002, CH10003... CH10010
4. Don't wait between scans

**Expected Result:**
- ✅ All 10 children processed correctly
- ✅ No scans missed
- ✅ No duplicate scans registered
- ✅ All children linked to parent SB10000
- ✅ System handles rapid input (< 1 second between scans)
- ✅ No errors or freezing

**Type:** POSITIVE (Performance)  
**Priority:** HIGH

---

### TC-034: Scan Invalid QR Code (NEGATIVE)
**Steps:**
1. Go to scanning page
2. Scan QR code with invalid format: `INVALID12@#$`
3. Observe result

**Expected Result:**
- ✅ Scan rejected
- ✅ Error message: "Invalid QR code format"
- ✅ Audio error beep (different from success beep)
- ✅ Red flash or error indicator
- ✅ Input field clears
- ✅ Ready for next scan
- ✅ No bag created with invalid QR

**Type:** NEGATIVE  
**Priority:** HIGH

---

### TC-035: Scan Already Linked Child (NEGATIVE)
**Steps:**
1. Link child CH99999 to parent SB11111
2. Try to scan and link same child CH99999 to parent SB22222

**Expected Result:**
- ✅ Link attempt fails
- ✅ Error: "Child already linked to another parent (SB11111)"
- ✅ Shows which parent it's linked to
- ✅ Option to unlink first if needed
- ✅ No second link created

**Type:** NEGATIVE  
**Priority:** HIGH

---

### TC-036: Undo Last Scan (POSITIVE)
**Steps:**
1. Scan parent: SB12345
2. Scan child: CH11111
3. Link created
4. Realize it was wrong scan
5. Click "Undo Last Scan" button within 1 hour

**Expected Result:**
- ✅ Undo button available (within 1 hour window)
- ✅ Click undo - confirmation popup
- ✅ After confirm: link removed
- ✅ Message: "Last scan undone successfully"
- ✅ Child CH11111 unlinked from parent
- ✅ Scan still in history but marked as undone
- ✅ Can't undo after 1 hour passes

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-037: Offline Scanning with Auto-Sync (POSITIVE)
**Steps:**
1. Login on mobile device
2. Disconnect from internet (turn off WiFi)
3. Scan parent and children
4. Reconnect to internet after 5 scans

**Expected Result:**
- ✅ Scans work offline (saved locally)
- ✅ Message: "Offline - scans will sync when online"
- ✅ After reconnecting: auto-sync happens
- ✅ Message: "5 scans synced successfully"
- ✅ All scans now in database
- ✅ Visual indicator during offline mode

**Type:** POSITIVE (Offline Feature)  
**Priority:** MEDIUM

---

### TC-038: View Scan History (POSITIVE)
**Steps:**
1. Login
2. Go to "Scan History" or "Activity Log"
3. View all scans

**Expected Result:**
- ✅ Shows list of all scans
- ✅ Each scan shows: Date/Time, User, Bag QR, Action
- ✅ Can filter by date
- ✅ Can filter by user
- ✅ Can filter by dispatch area
- ✅ Pagination works for large history
- ✅ Can export to CSV/Excel

**Type:** POSITIVE  
**Priority:** MEDIUM

---

## Section 5: Bill Management

**⚠️ REMINDER: All tests in this section MUST be run on DEVELOPMENT environment ONLY!**  
**NEVER create/modify/delete bills on production!**

---

### TC-039: Create New Bill (POSITIVE)
**Steps:**
1. Login as admin or biller
2. Go to "Bill Management"
3. Click "Create New Bill"
4. Fill in:
   - Customer Name: Test Customer
   - Dispatch Area: Lucknow
   - Transport Details: Truck ABC-123
5. Click "Create Bill"

**Expected Result:**
- ✅ Bill created successfully
- ✅ Message: "Bill created successfully"
- ✅ Bill number auto-generated (e.g., BILL-0001)
- ✅ Bill shows in bills list
- ✅ Status: Draft or Active
- ✅ No parent bags linked yet (empty)

**Type:** POSITIVE  
**Priority:** CRITICAL

---

### TC-040: Add Parent Bags to Bill (POSITIVE)
**Steps:**
1. Create a bill (from TC-039)
2. Open bill details
3. Click "Add Parent Bag"
4. Scan or enter parent bag QR: `SB12345`
5. Confirm addition

**Expected Result:**
- ✅ Parent bag added to bill
- ✅ Bill shows SB12345 in parent bags list
- ✅ Shows number of children for this parent
- ✅ Total weight calculated automatically
- ✅ Can add multiple parent bags to same bill

**Type:** POSITIVE  
**Priority:** CRITICAL

---

### TC-041: Remove Parent Bag from Bill (POSITIVE)
**Steps:**
1. Open bill with parent bags
2. Find a parent bag in the list
3. Click "Remove" button next to it
4. Confirm removal

**Expected Result:**
- ✅ Confirmation: "Remove bag from bill?"
- ✅ After confirm: bag removed from bill
- ✅ Message: "Bag removed from bill"
- ✅ Total weight recalculated
- ✅ Bag still exists, just not on this bill
- ✅ Can add it to another bill

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-042: Calculate Bill Weight Automatically (POSITIVE)
**Steps:**
1. Create bill
2. Add parent bag with 5 children
3. Add another parent with 3 children
4. View bill details

**Expected Result:**
- ✅ Total children count: 8
- ✅ Weight calculation: 8 children × 50kg = 400kg (or your formula)
- ✅ Weight updates automatically when bags added/removed
- ✅ Weight shown clearly on bill
- ✅ Can see breakdown by parent bag

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-043: Edit Bill Details (POSITIVE)
**Steps:**
1. Open existing bill
2. Click "Edit" button
3. Change customer name to "Updated Customer"
4. Change transport details
5. Click "Save Changes"

**Expected Result:**
- ✅ Changes saved successfully
- ✅ Message: "Bill updated successfully"
- ✅ Bill shows updated information
- ✅ Parent bags remain linked
- ✅ Audit log shows who edited and when

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-044: Complete/Finish Bill (POSITIVE)
**Steps:**
1. Open bill with parent bags
2. Click "Complete Bill" or "Finish Bill" button
3. Confirm completion

**Expected Result:**
- ✅ Confirmation: "Mark bill as completed?"
- ✅ After confirm: bill status = Completed
- ✅ Message: "Bill completed successfully"
- ✅ Bill locked (can't edit anymore)
- ✅ Parent bags locked to this bill
- ✅ Can print/export bill

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-045: Try to Edit Completed Bill (NEGATIVE)
**Steps:**
1. Find a completed bill
2. Try to click "Edit" button
3. Try to add/remove bags

**Expected Result:**
- ✅ Edit button disabled or not visible
- ✅ Message: "Cannot edit completed bill"
- ✅ No changes allowed
- ✅ Can only view bill details
- ✅ Can print/export only

**Type:** NEGATIVE (Business Rule)  
**Priority:** MEDIUM

---

### TC-046: Delete Bill (Admin Only) (POSITIVE)
**Steps:**
1. Login as admin
2. Find a draft/test bill
3. Click "Delete Bill" button
4. Confirm deletion

**Expected Result:**
- ✅ Confirmation: "Delete bill? This cannot be undone."
- ✅ After confirm: bill deleted
- ✅ Message: "Bill deleted successfully"
- ✅ Bill removed from list
- ✅ Parent bags unlinked from bill (available again)
- ✅ Can't delete completed bills (safety)

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-047: View Bill Details and Print (POSITIVE)
**Steps:**
1. Open any completed bill
2. Click "Print Bill" or "Download PDF" button

**Expected Result:**
- ✅ Bill opens in print preview
- ✅ Shows all details:
  - Bill number
  - Date
  - Customer name
  - Dispatch area
  - List of parent bags
  - Children count per parent
  - Total weight
  - Transport details
- ✅ Formatted nicely for printing
- ✅ Can save as PDF
- ✅ Can print on paper

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-048: Link Same Parent to Multiple Bills (NEGATIVE)
**Steps:**
1. Create Bill #1
2. Add parent SB12345 to Bill #1
3. Create Bill #2
4. Try to add same parent SB12345 to Bill #2

**Expected Result:**
- ✅ Addition fails
- ✅ Error: "Parent bag already on another bill (Bill #1)"
- ✅ Shows which bill it's on
- ✅ Can't double-bill same parent
- ✅ Must remove from Bill #1 first

**Type:** NEGATIVE (Business Rule)  
**Priority:** HIGH

---

## Section 6: Search & Filtering

### TC-049: Search Bags by QR Code (POSITIVE)
**Steps:**
1. Go to "Bag Management"
2. Use search box
3. Enter partial QR: `SB123`
4. Press Enter or click Search

**Expected Result:**
- ✅ Shows all bags with QR containing "SB123"
- ✅ Results: SB12345, SB12390, etc.
- ✅ Partial match works
- ✅ Case insensitive (SB123 = sb123)
- ✅ Fast results (under 1 second)

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-050: Filter Bags by Type (POSITIVE)
**Steps:**
1. Go to "Bag Management"
2. Use filter dropdown
3. Select "Parent Bags Only"
4. Apply filter

**Expected Result:**
- ✅ Shows only parent bags
- ✅ No child bags in results
- ✅ Can switch to "Child Bags Only"
- ✅ Can select "All Bags" to see both
- ✅ Filter persists during pagination

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-051: Filter Bills by Status (POSITIVE)
**Steps:**
1. Go to "Bill Management"
2. Use filter: "Active Bills"
3. Apply filter
4. Change to "Completed Bills"

**Expected Result:**
- ✅ Active Bills filter shows only draft/active bills
- ✅ Completed Bills filter shows only finished bills
- ✅ "All Bills" shows everything
- ✅ Count updates correctly
- ✅ Fast filtering (under 1 second)

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-052: Filter by Date Range (POSITIVE)
**Steps:**
1. Go to any list page (bags/bills/scans)
2. Use date filter
3. Select: From 2024-01-01 To 2024-12-31
4. Apply filter

**Expected Result:**
- ✅ Shows only items in date range
- ✅ Date picker works properly
- ✅ Can clear date filter
- ✅ Results update immediately
- ✅ Can export filtered results

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-053: Search with No Results (NEGATIVE)
**Steps:**
1. Search for QR: `DOESNOTEXIST999`
2. Press search

**Expected Result:**
- ✅ No results found
- ✅ Message: "No bags found matching your search"
- ✅ Helpful message: "Try different search term"
- ✅ Can clear search and try again
- ✅ No error or crash

**Type:** NEGATIVE  
**Priority:** LOW

---

### TC-054: Search by Dispatch Area (POSITIVE)
**Steps:**
1. Go to bag or bill list
2. Filter by dispatch area: "Lucknow"
3. Apply filter

**Expected Result:**
- ✅ Shows only items from Lucknow
- ✅ Can switch to other areas
- ✅ Admin/Biller sees all areas
- ✅ Dispatcher sees only their area
- ✅ Count accurate per area

**Type:** POSITIVE  
**Priority:** MEDIUM

---

## Section 7: Reports & Data Export

### TC-055: Export Bags to CSV (POSITIVE)
**Steps:**
1. Go to "Bag Management" or "Reports"
2. Click "Export to CSV" button
3. Download file

**Expected Result:**
- ✅ CSV file downloads successfully
- ✅ Filename: bags_export_2024-11-20.csv (with date)
- ✅ Contains all bag data:
  - ID, QR Code, Type, Created Date, Created By
- ✅ Can open in Excel/Google Sheets
- ✅ All data readable
- ✅ Proper formatting (no weird characters)

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-056: Export Bills to Excel (POSITIVE)
**Steps:**
1. Go to "Bill Management" or "Reports"
2. Click "Export to Excel" button
3. Download file

**Expected Result:**
- ✅ Excel file (.xlsx) downloads
- ✅ Filename: bills_export_2024-11-20.xlsx
- ✅ Contains all bill data:
  - Bill Number, Customer, Date, Status, Weight, Parent Bags
- ✅ Opens in Excel properly
- ✅ Multiple sheets if needed (Bills, Details)
- ✅ Formatted nicely

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-057: Generate User Activity Report (Admin Only) (POSITIVE)
**Steps:**
1. Login as admin
2. Go to "Reports" → "User Activity"
3. Select date range: Last 7 days
4. Click "Generate Report"

**Expected Result:**
- ✅ Report generates successfully
- ✅ Shows per user:
  - Total scans
  - Bags created
  - Bills created
  - Last login
  - Active hours
- ✅ Can export to CSV/Excel
- ✅ Visual charts/graphs (optional)

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-058: Generate Daily Summary Report (POSITIVE)
**Steps:**
1. Go to "Reports" → "Daily Summary"
2. Select today's date
3. Generate report

**Expected Result:**
- ✅ Shows today's statistics:
  - Total bags scanned
  - New bags created
  - Bills completed
  - Active users
  - Peak hours
- ✅ Comparison with yesterday
- ✅ Can print or export
- ✅ Auto-generated at end of day (optional)

**Type:** POSITIVE  
**Priority:** LOW

---

### TC-059: Export Large Dataset (POSITIVE - Performance)
**Steps:**
1. Try to export 10,000+ bags
2. Click "Export All to CSV"
3. Wait for download

**Expected Result:**
- ✅ Export completes (may take 30-60 seconds)
- ✅ Progress indicator shows "Generating export..."
- ✅ File downloads successfully
- ✅ All 10,000+ records in file
- ✅ No timeout errors
- ✅ Can open file without Excel crashing

**Type:** POSITIVE (Performance)  
**Priority:** MEDIUM

---

## Section 8: Admin Features

**⚠️ REMINDER: All tests in this section MUST be run on DEVELOPMENT environment ONLY!**  
**Use test_admin account - NEVER use production admin for testing!**

---

### TC-060: View System Health Dashboard (Admin Only) (POSITIVE)
**Steps:**
1. Login as admin
2. Go to "System Health" or "Admin" → "System Monitor"

**Expected Result:**
- ✅ Page loads with real-time metrics:
  - Database connection status
  - Connection pool usage (X out of 80 connections)
  - Cache hit rate percentage
  - Memory usage
  - Database size
  - Active users count
  - Error rate
- ✅ All metrics show green/healthy status
- ✅ Updates automatically every 30 seconds
- ✅ Can see historical graphs (optional)

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-061: Clear Cache (Admin Only) (POSITIVE)
**Steps:**
1. Login as admin
2. Go to "System Health" or "Admin Panel"
3. Find "Clear Cache" button
4. Click it
5. Confirm

**Expected Result:**
- ✅ Confirmation: "Clear all cached data?"
- ✅ After confirm: cache cleared
- ✅ Message: "Cache cleared successfully"
- ✅ Next page loads will rebuild cache
- ✅ No data lost (cache only, not database)
- ✅ System performance may be slower temporarily

**Type:** POSITIVE  
**Priority:** LOW

---

### TC-062: View Audit Logs (Admin Only) (POSITIVE)
**Steps:**
1. Login as admin
2. Go to "Audit Logs" or "Admin" → "Activity Log"
3. View all audit entries

**Expected Result:**
- ✅ Shows comprehensive audit trail:
  - Who did what
  - When (date/time)
  - What changed (before/after values)
  - IP address
  - Action type (create/update/delete)
- ✅ Can filter by:
  - User
  - Action type
  - Date range
  - Entity type (bag/bill/user)
- ✅ Can search audit logs
- ✅ Can export audit trail

**Type:** POSITIVE  
**Priority:** HIGH

---

### TC-063: Promote User to Admin (POSITIVE)
**Steps:**
1. Login as admin
2. Go to "User Management"
3. Find a biller or dispatcher
4. Click "Promote to Admin"
5. Confirm promotion

**Expected Result:**
- ✅ Confirmation: "Promote user to Admin?"
- ✅ After confirm: user role = admin
- ✅ Message: "User promoted successfully"
- ✅ User now has admin privileges
- ✅ Logged in audit trail
- ✅ User gets notification (if enabled)

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-064: Demote Admin to Regular User (POSITIVE)
**Steps:**
1. Login as admin
2. Find another admin (not yourself!)
3. Click "Demote" or "Change Role"
4. Set role to Biller
5. Confirm

**Expected Result:**
- ✅ Confirmation required
- ✅ Can't demote yourself (safety)
- ✅ Role changed successfully
- ✅ User loses admin access
- ✅ Logged in audit trail

**Type:** POSITIVE  
**Priority:** MEDIUM

---

### TC-065: View Database Statistics (Admin Only) (POSITIVE)
**Steps:**
1. Login as admin
2. Go to "System Health" → "Database Stats"

**Expected Result:**
- ✅ Shows:
  - Total bags: 344,683+ (production number)
  - Total parent bags
  - Total child bags
  - Total bills
  - Total users
  - Database size in MB/GB
  - Largest tables
  - Index health
- ✅ All numbers accurate
- ✅ Can see table details

**Type:** POSITIVE  
**Priority:** LOW

---

### TC-066: Try Admin Features as Non-Admin (NEGATIVE)
**Steps:**
1. Login as dispatcher or biller
2. Try to access /admin/user_management by typing URL
3. Try to access /admin/system_health

**Expected Result:**
- ✅ Access denied
- ✅ Redirected to dashboard or login
- ✅ Error: "Unauthorized access" or similar
- ✅ No data exposed
- ✅ Attempt logged in audit trail

**Type:** NEGATIVE (Security)  
**Priority:** CRITICAL

---

## Section 9: Security Features

### TC-067: CSRF Protection on Forms (POSITIVE)
**Steps:**
1. Login
2. Open any form (create bag, create bill, etc.)
3. Open browser dev tools (F12)
4. Look at form HTML for CSRF token
5. Try to submit form without token

**Expected Result:**
- ✅ All forms have hidden CSRF token field
- ✅ Form submission without valid token fails
- ✅ Error: "CSRF token missing or invalid"
- ✅ No data saved without token
- ✅ Protection against CSRF attacks

**Type:** POSITIVE (Security)  
**Priority:** HIGH

---

### TC-068: SQL Injection Prevention (NEGATIVE)
**Steps:**
1. Go to search box
2. Try malicious input: `' OR '1'='1`
3. Submit search

**Expected Result:**
- ✅ Search treats it as literal text
- ✅ No SQL error messages
- ✅ No unauthorized data exposed
- ✅ System sanitizes input properly
- ✅ No security breach

**Type:** NEGATIVE (Security)  
**Priority:** CRITICAL

---

### TC-069: XSS Prevention (NEGATIVE)
**Steps:**
1. Try to create bag with QR: `<script>alert('XSS')</script>`
2. Save and view bag details

**Expected Result:**
- ✅ Script not executed
- ✅ Displayed as plain text: `<script>alert('XSS')</script>`
- ✅ HTML escaped properly
- ✅ No JavaScript popup
- ✅ No security risk

**Type:** NEGATIVE (Security)  
**Priority:** CRITICAL

---

### TC-070: Rate Limiting on Login (NEGATIVE)
**Steps:**
1. Try to login 1000 times rapidly
2. Use automated tool or script

**Expected Result:**
- ✅ After certain attempts (e.g., 20), rate limit kicks in
- ✅ Error: "Too many requests, please wait"
- ✅ Temporarily blocked (e.g., 1 hour)
- ✅ Prevents brute force attacks
- ✅ Admin can see blocked IPs

**Type:** NEGATIVE (Security)  
**Priority:** HIGH

---

### TC-071: Session Hijacking Prevention (POSITIVE)
**Steps:**
1. Login and get session cookie
2. Try to use same session from different browser/computer
3. Try to modify session cookie

**Expected Result:**
- ✅ Session tied to IP address (optional but recommended)
- ✅ Modified cookie rejected
- ✅ User logged out if session tampered
- ✅ Secure cookie flags set (HttpOnly, Secure)
- ✅ Session expires after logout

**Type:** POSITIVE (Security)  
**Priority:** HIGH

---

### TC-072: Password Complexity Check (POSITIVE)
**Steps:**
1. Try to create user with password: `123`
2. Try password: `password`
3. Try password: `Admin@12345` (strong)

**Expected Result:**
- ✅ Weak passwords rejected
- ✅ Error: "Password must be at least 8 characters"
- ✅ Strong password accepted
- ✅ Password strength indicator (optional)
- ✅ Enforces security policy

**Type:** POSITIVE (Security)  
**Priority:** MEDIUM

---

### TC-073: Audit Trail Integrity (POSITIVE)
**Steps:**
1. Login as admin
2. Create a bag
3. Edit the bag
4. Delete the bag
5. View audit logs

**Expected Result:**
- ✅ All 3 actions logged:
  - Created: who, when, what
  - Updated: who, when, before/after values
  - Deleted: who, when, what was deleted
- ✅ Timestamps accurate
- ✅ User info correct
- ✅ Can't modify or delete audit logs
- ✅ Complete trail of all actions

**Type:** POSITIVE (Security & Compliance)  
**Priority:** HIGH

---

## Section 10: Mobile Testing

### TC-074: Mobile Login (POSITIVE)
**Steps:**
1. Open website on mobile phone (Android/iPhone)
2. Go to login page
3. Login with admin credentials

**Expected Result:**
- ✅ Page displays properly on mobile
- ✅ Input fields sized correctly
- ✅ Keyboard pops up for text input
- ✅ Login button large and tappable
- ✅ No horizontal scrolling needed
- ✅ Login successful
- ✅ Mobile-friendly layout

**Type:** POSITIVE (Mobile)  
**Priority:** HIGH

---

### TC-075: Mobile Dashboard (POSITIVE)
**Steps:**
1. Login on mobile
2. View dashboard

**Expected Result:**
- ✅ Dashboard responsive on small screen
- ✅ Statistics cards stack vertically
- ✅ All data visible without zooming
- ✅ Touch targets large enough (min 44x44px)
- ✅ No overlapping elements
- ✅ Charts/graphs mobile-friendly
- ✅ Fast loading on mobile network

**Type:** POSITIVE (Mobile)  
**Priority:** HIGH

---

### TC-076: Mobile Scanning with Scanner Device (POSITIVE)
**Steps:**
1. Use warehouse scanner tablet/phone
2. Go to scan parent page
3. Use attached Bluetooth scanner
4. Scan multiple bags

**Expected Result:**
- ✅ Scanner connects via Bluetooth
- ✅ Scans captured automatically
- ✅ Large scan results visible
- ✅ Audio feedback loud enough to hear
- ✅ Vibration feedback (if supported)
- ✅ Can scan rapid-fire (10+ per minute)
- ✅ No lag or freezing
- ✅ Works offline with sync

**Type:** POSITIVE (Mobile + Hardware)  
**Priority:** CRITICAL

---

### TC-077: Mobile Navigation (POSITIVE)
**Steps:**
1. Login on mobile
2. Use navigation menu
3. Navigate between pages

**Expected Result:**
- ✅ Hamburger menu or bottom nav bar
- ✅ Menu opens smoothly
- ✅ All pages accessible
- ✅ Back button works properly
- ✅ No broken links
- ✅ Quick access to scan functions
- ✅ Easy to navigate one-handed

**Type:** POSITIVE (Mobile)  
**Priority:** HIGH

---

### TC-078: Mobile Form Entry (POSITIVE)
**Steps:**
1. On mobile, go to "Create Bill" form
2. Fill in all fields
3. Submit form

**Expected Result:**
- ✅ Form fields sized for mobile
- ✅ Proper keyboard for each field type:
  - Text keyboard for names
  - Number keyboard for numbers
  - Email keyboard for email
- ✅ Date picker mobile-friendly
- ✅ Dropdown menus work smoothly
- ✅ Submit button easily tappable
- ✅ Form validation clear

**Type:** POSITIVE (Mobile)  
**Priority:** MEDIUM

---

### TC-079: Mobile Portrait vs Landscape (POSITIVE)
**Steps:**
1. Login on mobile
2. View dashboard in portrait mode
3. Rotate to landscape mode
4. Navigate to different pages

**Expected Result:**
- ✅ Layout adjusts to both orientations
- ✅ No content cut off in landscape
- ✅ Tables more readable in landscape
- ✅ Forms still usable in both modes
- ✅ No broken layouts
- ✅ Smooth transition between modes

**Type:** POSITIVE (Mobile)  
**Priority:** MEDIUM

---

### TC-080: Mobile Offline Mode (POSITIVE)
**Steps:**
1. Login on mobile
2. Turn off WiFi/data
3. Try to scan bags
4. Reconnect after 10 scans

**Expected Result:**
- ✅ Offline indicator appears
- ✅ Can still scan bags (saved locally)
- ✅ Queue shows "10 scans pending sync"
- ✅ After reconnect: auto-sync starts
- ✅ All 10 scans uploaded successfully
- ✅ Message: "Synced successfully"
- ✅ No data lost

**Type:** POSITIVE (Mobile + Offline)  
**Priority:** HIGH

---

## Section 11: Load Testing

### TC-081: 10 Concurrent Users (POSITIVE)
**Steps:**
1. Have 10 people login simultaneously
2. Each person scans bags at same time
3. All create bills together
4. Monitor system performance

**Expected Result:**
- ✅ All 10 users can login
- ✅ No slowdown or errors
- ✅ All scans processed correctly
- ✅ No duplicate scans
- ✅ Database handles concurrent writes
- ✅ Response time under 2 seconds per action
- ✅ No crashes or freezing

**Type:** POSITIVE (Load Test)  
**Priority:** HIGH

---

### TC-082: 50 Concurrent Users (POSITIVE)
**Steps:**
1. Simulate 50 users accessing system
2. Mix of activities:
   - 20 scanning bags
   - 15 creating bills
   - 10 searching
   - 5 viewing reports
3. Run for 30 minutes

**Expected Result:**
- ✅ System handles 50 concurrent users
- ✅ Response time under 3 seconds
- ✅ Database pool has enough connections (80 max)
- ✅ No connection errors
- ✅ All transactions complete successfully
- ✅ Memory usage acceptable
- ✅ CPU usage under 80%

**Type:** POSITIVE (Load Test)  
**Priority:** HIGH

---

### TC-083: 100 Concurrent Users (POSITIVE)
**Steps:**
1. Simulate 100 users (production target)
2. Heavy activity for 1 hour
3. Monitor all metrics

**Expected Result:**
- ✅ System stable with 100 users
- ✅ Response time under 5 seconds (acceptable)
- ✅ Database pool usage under 95%
- ✅ Cache working effectively (80%+ hit rate)
- ✅ No crashes or errors
- ✅ All features functional
- ✅ Memory doesn't leak over time

**Type:** POSITIVE (Load Test)  
**Priority:** CRITICAL

---

### TC-084: Stress Test - Beyond Capacity (NEGATIVE)
**Steps:**
1. Simulate 200+ users (beyond design)
2. All scanning rapidly
3. Push system to limits

**Expected Result:**
- ✅ System degrades gracefully (no crash)
- ✅ Slower response time but still functional
- ✅ Queue requests if needed
- ✅ Rate limiting kicks in
- ✅ Error messages helpful: "High load, please wait"
- ✅ System recovers when load decreases
- ✅ No data corruption

**Type:** NEGATIVE (Stress Test)  
**Priority:** MEDIUM

---

### TC-085: Database Performance with 1.8M Bags (POSITIVE)
**Steps:**
1. With production data (1.8 million bags)
2. Search for specific bag
3. Create new bags
4. Generate reports

**Expected Result:**
- ✅ Search returns results in under 1 second
- ✅ Database indexes working (optimized queries)
- ✅ Create bag operation under 500ms
- ✅ Dashboard loads in under 2 seconds
- ✅ Pagination works smoothly
- ✅ No timeout errors
- ✅ System scales to 1.8M+ bags

**Type:** POSITIVE (Performance)  
**Priority:** CRITICAL

---

### TC-086: Peak Hours Simulation (POSITIVE)
**Steps:**
1. Simulate morning rush (8-10 AM)
2. 60+ users scanning simultaneously
3. Heavy bill creation activity
4. Multiple report generations

**Expected Result:**
- ✅ System handles peak load
- ✅ No significant slowdown
- ✅ Auto-scaling works (if configured)
- ✅ All critical functions remain fast
- ✅ Background tasks queued properly
- ✅ Users don't notice degradation

**Type:** POSITIVE (Load Test)  
**Priority:** HIGH

---

## Section 12: Error Handling

### TC-087: Database Connection Loss (NEGATIVE)
**Steps:**
1. Simulate database disconnect (admin action)
2. Try to perform operations
3. Reconnect database

**Expected Result:**
- ✅ Graceful error message: "Database temporarily unavailable"
- ✅ No crash or white screen
- ✅ Auto-retry connection
- ✅ When DB returns: system recovers automatically
- ✅ User can continue working
- ✅ Pending operations queued

**Type:** NEGATIVE (Error Handling)  
**Priority:** HIGH

---

### TC-088: Network Timeout (NEGATIVE)
**Steps:**
1. On mobile device
2. Start scanning
3. Simulate very slow network (3G or worse)
4. Complete scan operation

**Expected Result:**
- ✅ Loading indicator shows "Please wait..."
- ✅ Operation waits up to 30 seconds
- ✅ If timeout: clear error message
- ✅ Option to retry
- ✅ Offline queue catches failed operations
- ✅ No silent failures

**Type:** NEGATIVE (Error Handling)  
**Priority:** MEDIUM

---

### TC-089: Form Validation Errors (NEGATIVE)
**Steps:**
1. Try to create bill without required fields
2. Submit empty form

**Expected Result:**
- ✅ Submission blocked
- ✅ Red highlights on missing fields
- ✅ Error messages clear and specific:
  - "Customer name is required"
  - "Dispatch area is required"
- ✅ Focus jumps to first error
- ✅ Can fix and resubmit
- ✅ No data saved with validation errors

**Type:** NEGATIVE (Error Handling)  
**Priority:** MEDIUM

---

### TC-090: File Upload Error (NEGATIVE)
**Steps:**
1. Try to upload very large file (>100MB)
2. Try to upload wrong file type (.exe instead of .csv)

**Expected Result:**
- ✅ Large file rejected: "File too large (max 10MB)"
- ✅ Wrong type rejected: "Invalid file type"
- ✅ Clear error messages
- ✅ Can try again with correct file
- ✅ No server crash

**Type:** NEGATIVE (Error Handling)  
**Priority:** LOW

---

### TC-091: Concurrent Edit Conflict (NEGATIVE)
**Steps:**
1. User A opens Bill #123 for editing
2. User B opens same Bill #123 for editing
3. User A saves changes
4. User B tries to save different changes

**Expected Result:**
- ✅ User B gets warning: "Bill was modified by another user"
- ✅ Option to:
  - View latest changes
  - Overwrite anyway (admin only)
  - Cancel
- ✅ No data lost
- ✅ Conflict resolution clear

**Type:** NEGATIVE (Concurrency)  
**Priority:** MEDIUM

---

### TC-092: Server Error (500) Handling (NEGATIVE)
**Steps:**
1. Trigger internal server error (if possible)
2. Observe error page

**Expected Result:**
- ✅ Custom error page (not default server page)
- ✅ Message: "Something went wrong. Our team has been notified."
- ✅ Error ID shown for support reference
- ✅ Link to go back home
- ✅ Error logged for admin review
- ✅ User can continue using other features

**Type:** NEGATIVE (Error Handling)  
**Priority:** MEDIUM

---

### TC-093: Permission Denied (403) Handling (NEGATIVE)
**Steps:**
1. Login as dispatcher
2. Try to access admin-only URL: /admin/users
3. Observe response

**Expected Result:**
- ✅ Access denied page
- ✅ Message: "You don't have permission to access this page"
- ✅ Not showing sensitive info
- ✅ Link to go back
- ✅ Attempt logged in audit trail
- ✅ No security vulnerability

**Type:** NEGATIVE (Error Handling)  
**Priority:** HIGH

---

## 📊 Summary & Reporting

### After Testing

**For Each Section, Count:**
- ✅ Total Passed
- ❌ Total Failed  
- ⚠️ Total Partial

**Overall Test Results:**
```
Total Test Cases: 93
Passed: ___
Failed: ___
Partial: ___
Pass Rate: ___%
```

**Critical Issues Found:**
1. _____________________
2. _____________________
3. _____________________

**Medium Issues Found:**
1. _____________________
2. _____________________

**Low Priority Issues:**
1. _____________________
2. _____________________

**Notes:**
- Test environment: Production / Development
- Test date: __________
- Tester name: __________
- Browser used: __________
- Mobile device used: __________

---

## 🎯 Priority Guide

**CRITICAL (Must Fix Before Launch):**
- Login/Authentication
- Bag scanning
- Bill creation
- Data integrity
- Security vulnerabilities
- System crashes

**HIGH (Fix Soon):**
- Search functionality
- Reports
- User management
- Performance issues
- Data loss risks

**MEDIUM (Fix When Possible):**
- UI improvements
- Minor bugs
- Convenience features
- Optimization

**LOW (Nice to Have):**
- Visual polish
- Extra features
- Documentation
- Small usability issues

---

## 📞 Support Contacts

**For Test Issues:**
- Technical Lead: [Contact]
- System Admin: admin@traitortrack.com
- Database: DBA team

**For Access Issues:**
- Request test account credentials from system administrator
- Specify which role you need (admin, biller, dispatcher)
- Confirm you need DEVELOPMENT environment access only
- Emergency production issues: Contact system admin directly (do not test on production!)

---

**End of Test Cases Document**

*Last Updated: November 20, 2025*  
*Version: 2.0*  
*Total Test Cases: 93*

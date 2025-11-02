# TraitorTrack User Guide for Dispatchers & Billers

**Version:** 1.0.0  
**Last Updated:** November 2025  
**Audience:** Dispatchers and Billers

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Bag Scanning Workflows](#bag-scanning-workflows)
4. [Bill Generation & Management](#bill-generation--management)
5. [Search & Filtering](#search--filtering)
6. [Reports & Exports](#reports--exports)
7. [Common Tasks & Tips](#common-tasks--tips)
8. [Troubleshooting](#troubleshooting)
9. [Frequently Asked Questions](#frequently-asked-questions)

---

## Getting Started

### System Access

1. **Login Page**: Navigate to `https://your-domain.com/login`
2. **Enter credentials**:
   - Username or email
   - Password
3. **Click "Login"**

**First-time users**: Contact your administrator to create an account.

### User Roles

**Dispatcher**:
- Scan parent and child bags
- Link child bags to parent bags
- View bag information
- Access to assigned dispatch area only

**Biller**:
- All dispatcher capabilities
- Create and manage bills
- Link parent bags to bills
- Generate reports
- Access to all dispatch areas

### System Requirements

- **Browser**: Chrome, Firefox, Safari, or Edge (latest version)
- **Internet**: Stable connection required
- **Scanner**: Wireless 2D barcode scanner (keyboard wedge mode)
  - Recommended: Coconut wireless scanner or equivalent

---

## Dashboard Overview

### Main Dashboard

Access: Click "Dashboard" from the navigation menu

**Quick Stats** (updated in real-time):
- Total Bags (Parent + Child)
- Total Bills
- Recent Scans (Last 24 Hours)
- Your Recent Activity

**Navigation Menu**:
- 🏠 **Dashboard** - Main overview
- 📦 **Scan Bag** - Quick scan interface
- 🔍 **Search** - Find bags and bills
- 📋 **Bills** - Bill management (Billers only)
- 👤 **Profile** - Your account settings

### Your Profile

Access: Click your name in the top-right corner → "Profile"

**View**:
- Username
- Email address
- Role (Dispatcher/Biller)
- Dispatch area (Dispatchers only)
- Account created date

**Actions**:
- Change password
- Update email address
- View your scanning history

---

## Bag Scanning Workflows

### Understanding Bag Types

**Parent Bag**:
- Large bag containing multiple child bags
- QR code starts with "SB" (e.g., SB123456)
- Capacity: Up to 30 child bags
- Weight: Calculated based on child bags (1kg per child)

**Child Bag**:
- Smaller individual bag
- Unique QR code (any format except "SB")
- Weight: 1kg each
- Must be linked to a parent bag

### Scan Parent Bag

**Method 1: Quick Scan**

1. Click "**Scan Bag**" in navigation
2. Focus cursor in the QR code field
3. **Scan parent bag** with barcode scanner
4. System automatically:
   - Creates parent bag if new
   - Displays bag information
   - Prompts for child bag scanning

**Method 2: Manual Entry**

1. Click "Scan Bag"
2. Type parent bag QR code (e.g., SB123456)
3. Click "Submit" or press Enter

**Expected Result**:
- ✅ "Parent bag SB123456 scanned successfully"
- You'll see:
  - Bag QR code
  - Bag type: Parent
  - Number of children (if any)
  - Created date
  - Your dispatch area

### Scan Child Bags

**Workflow**: After scanning parent bag

1. Parent bag information displays
2. **Scan child bag** with barcode scanner
3. System automatically:
   - Creates child bag if new
   - Links child to parent
   - Updates parent bag count
4. **Repeat** for all child bags (up to 30)
5. Click "Complete" when done

**Rapid Scanning Tips**:
- Keep scanner within range
- Scan at consistent angle
- Wait for beep confirmation
- System processes <200ms per scan

**Progress Tracking**:
- Real-time child count: "15/30 children scanned"
- Visual progress bar
- List of scanned children

### Link Child to Different Parent

**Scenario**: Child bag scanned to wrong parent

1. Go to "**Search**" → Find the child bag
2. Click on child bag QR code
3. Click "**Relink to Parent**"
4. Scan or enter correct parent bag QR
5. Confirm relinking

**System Actions**:
- Removes link from old parent
- Creates link to new parent
- Updates both parent bag counts
- Logs action in audit trail

### View Bag Details

1. Click "**Search**"
2. Enter bag QR code
3. Click "Search"

**Information Displayed**:
- QR code
- Bag type (Parent/Child)
- Created date
- Dispatch area
- **For Parent Bags**:
  - Child count (e.g., 25/30)
  - Linked children list
  - Associated bill (if any)
  - Total weight
- **For Child Bags**:
  - Parent bag (if linked)
  - Link date
  - Scanner who linked it

---

## Bill Generation & Management

*Note: Bill management is available to Billers only. Dispatchers can view bills but cannot create or edit them.*

### Create New Bill

1. Click "**Bills**" in navigation
2. Click "**Create New Bill**"
3. Fill in bill details:
   - **Bill ID**: Unique identifier (e.g., BILL-2025-001)
   - **Description**: Optional (e.g., "Lucknow Dispatch - Nov 25")
4. Click "Create Bill"

**Expected Result**:
- ✅ "Bill BILL-2025-001 created successfully"
- Bill status: New

### Link Parent Bags to Bill

**Method 1: During Scanning**

1. After scanning parent bag with all children
2. Click "**Link to Bill**"
3. Select existing bill or create new one
4. Confirm linking

**Method 2: From Bill Page**

1. Go to "Bills" → Select bill
2. Click "**Add Parent Bags**"
3. Scan parent bag QR codes
4. System adds each parent to bill
5. Click "Done" when finished

**Automatic Calculations**:
- **Parent Bag Count**: Number of parent bags linked
- **Total Child Bags**: Sum of all children across parent bags
- **Actual Weight**: Total weight based on child count (1kg per child)
- **Expected Weight**: Parent count × 30kg (full capacity)
- **Weight Variance**: Difference between actual and expected

**Example**:
- Parent bags: 5
- Total children: 128
- Actual weight: 128kg
- Expected weight: 150kg (5 × 30)
- Variance: -22kg (22kg under capacity)

### View Bill Details

1. Click "**Bills**"
2. Click on bill ID

**Information Displayed**:
- Bill ID
- Description
- Status (New/Processing/Completed)
- Parent bag count
- Total child bags
- Actual weight vs. Expected weight
- Created by (username)
- Created date
- **Linked Parent Bags**:
  - QR codes
  - Child counts
  - Individual weights

### Edit Bill

1. Open bill details page
2. Click "**Edit Bill**"
3. Modify:
   - Description
   - Status
4. Add or remove parent bags
5. Click "**Save Changes**"

**System Actions**:
- Recalculates weights automatically
- Updates timestamps
- Logs changes in audit trail

### Generate Bill Report

1. Open bill details page
2. Click "**Generate Report**"
3. Select format:
   - PDF (printable)
   - Excel (editable)
   - CSV (data export)
4. Click "Download"

**Report Contents**:
- Bill summary
- Parent bag list with QR codes
- Child bag counts per parent
- Weight calculations
- Created by and date
- Status

---

## Search & Filtering

### Quick Search

**Search Box** (top navigation):
1. Enter QR code, bill ID, or keyword
2. Press Enter or click Search icon

**Search Results**:
- Bags matching QR code
- Bills matching ID
- Users matching name (Admins only)

### Advanced Bag Search

1. Click "**Search**" → "Advanced"
2. Filter by:
   - **Bag Type**: Parent, Child, or All
   - **Dispatch Area**: Your area or All (Billers)
   - **Date Range**: From/To dates
   - **Status**: Pending, Completed
3. Click "**Search**"

**Sort Options**:
- Newest first
- Oldest first
- QR code (A-Z)

### Filter Bills

1. Go to "**Bills**"
2. Use filters:
   - **Status**: New, Processing, Completed
   - **Date Range**: Custom dates
   - **Created By**: Username (Billers)
3. Results update automatically

---

## Reports & Exports

### Daily Scan Report

**Purpose**: Track your daily scanning activity

1. Click "**Reports**" → "Daily Scan Report"
2. Select date (default: today)
3. Click "Generate"

**Report Contents**:
- Total bags scanned
- Parent bags: count
- Child bags: count
- Scans per hour (chart)
- Your dispatch area summary

**Export**: PDF or Excel

### Bill Summary Report

**Purpose**: End-of-day billing summary

1. Click "**Reports**" → "Bill Summary"
2. Select date range
3. Filter by status (optional)
4. Click "Generate"

**Report Contents**:
- Total bills created
- Total parent bags
- Total weight (actual vs. expected)
- Weight variance analysis
- Bill status breakdown

**Export**: PDF, Excel, or CSV

### Dispatch Area Report

**Purpose**: Area-specific activity (Billers only)

1. Click "**Reports**" → "Dispatch Area Report"
2. Select:
   - Dispatch area
   - Date range
3. Click "Generate"

**Report Contents**:
- Bags scanned by area
- Active dispatchers
- Bills created
- Weight statistics
- Performance metrics

---

## Common Tasks & Tips

### Daily Workflow (Dispatcher)

**Morning Setup**:
1. Login to TraitorTrack
2. Check dashboard for pending bags
3. Prepare scanner (charge, test)

**During Shift**:
1. Scan parent bags as they arrive
2. Scan child bags immediately
3. Complete linking before next parent
4. Verify child counts (visual check)

**End of Shift**:
1. Complete any pending scans
2. Verify all bags linked
3. Logout

### Daily Workflow (Biller)

**Morning**:
1. Review overnight scans
2. Check pending bills
3. Generate previous day's reports

**During Day**:
1. Create bills for completed parent bags
2. Link parent bags to appropriate bills
3. Monitor weight variances
4. Handle any relinking requests

**End of Day**:
1. Complete all bills
2. Generate EOD summary report
3. Email reports to management (if configured)
4. Logout

### Efficiency Tips

**Scanning**:
- ✅ Scan in batch (multiple parents, then children)
- ✅ Use rapid scan mode for high volume
- ✅ Keep scanner close to screen
- ❌ Don't scan one-at-a-time if handling multiple bags
- ❌ Don't switch between parents before completing children

**Bill Management**:
- ✅ Create bills in advance for known shipments
- ✅ Use descriptive bill IDs (e.g., LUCKNOW-2025-11-25)
- ✅ Link parent bags immediately after scanning
- ❌ Don't wait until end of day to create bills
- ❌ Don't link incomplete parent bags to bills

**Accuracy**:
- ✅ Verify child count matches physical bags
- ✅ Double-check parent QR before scanning children
- ✅ Review bill weights before finalizing
- ❌ Don't rush during scanning
- ❌ Don't assume scanner always reads correctly

### Keyboard Shortcuts

- `Ctrl+/` or `Cmd+/` - Focus search box
- `Ctrl+S` or `Cmd+S` - Quick scan
- `Ctrl+B` or `Cmd+B` - View bills
- `Esc` - Cancel current operation

---

## Troubleshooting

### Scanner Issues

#### Scanner not working

**Symptoms**: Beeps but nothing appears on screen

**Solutions**:
1. ✅ Check scanner battery
2. ✅ Verify USB receiver is connected
3. ✅ Click in QR code input field
4. ✅ Test scanner in Notepad/TextEdit
5. ✅ Restart scanner (power off/on)

#### Duplicate scans

**Symptoms**: Same bag scanned twice

**Solution**:
- System prevents duplicates automatically
- You'll see: ⚠️ "Bag already linked to this parent"
- Safe to continue scanning

#### Scanner reads partial code

**Symptoms**: Incomplete QR code entered

**Solutions**:
1. ✅ Hold scanner steadier
2. ✅ Clean scanner lens
3. ✅ Adjust angle (90 degrees)
4. ✅ Move closer to barcode
5. ✅ Check barcode quality (not damaged)

### Application Issues

#### "Session expired" error

**Cause**: Inactive for >30 minutes

**Solution**:
1. Click "Login" again
2. Enter credentials
3. Resume work (unsaved data may be lost)

**Prevention**: Save work frequently, stay active

#### Slow performance

**Symptoms**: Delays >5 seconds

**Solutions**:
1. ✅ Refresh page (F5)
2. ✅ Clear browser cache
3. ✅ Close other tabs
4. ✅ Check internet connection
5. ⚠️ Contact admin if persistent

#### Can't find bag

**Symptoms**: Search returns no results

**Checks**:
1. Verify QR code spelling (case-insensitive)
2. Check for extra spaces
3. Try partial search (first few characters)
4. Verify bag exists (scan history)
5. Contact admin if still missing

### Bag Management Issues

#### Child linked to wrong parent

**Solution**: Relink (see [Link Child to Different Parent](#link-child-to-different-parent))

#### Parent bag shows wrong child count

**Symptoms**: Count doesn't match physical bags

**Checks**:
1. Refresh page
2. View parent bag details
3. Check child list for duplicates
4. Verify all children scanned

**If incorrect**:
- Contact administrator
- Provide parent QR code
- Describe discrepancy

#### Can't link child to parent

**Possible Causes**:
- Child already linked to another parent
- Parent at maximum capacity (30 children)
- Parent bag not created yet

**Solutions**:
1. Check child bag details (see current parent)
2. Relink if needed
3. Verify parent bag exists
4. Contact admin if error persists

### Bill Issues

#### Bill weights don't match

**Check**:
1. Refresh bill page
2. Click "Recalculate Weights"
3. Verify all parent bags linked
4. Check individual parent child counts

**If still incorrect**: Contact administrator

#### Can't create bill

**Possible Causes**:
- Bill ID already exists
- Missing required fields
- Permission issue (Dispatchers cannot create bills)

**Solutions**:
1. Use unique bill ID
2. Fill all required fields
3. Verify you have Biller role

---

## Frequently Asked Questions

### General

**Q: How do I change my password?**

A: Click your name → Profile → "Change Password"

**Q: What if I forget my password?**

A: Click "Forgot Password" on login page → Enter email → Check email for reset link

**Q: Can I access TraitorTrack on my phone?**

A: Yes! The interface is mobile-responsive. Use any modern mobile browser.

**Q: What browsers are supported?**

A: Chrome, Firefox, Safari, Edge (latest versions). Chrome recommended for best performance.

### Scanning

**Q: What's the difference between parent and child bags?**

A: Parent bags (QR starts with "SB") are large bags containing up to 30 smaller child bags. Child bags are individual items linked to parent bags.

**Q: Can I scan child bags without a parent?**

A: Technically yes, but they won't be linked. Always scan parent first, then children.

**Q: What if I scan child bags in the wrong order?**

A: Order doesn't matter! System links them automatically. Scan in any order.

**Q: Maximum child bags per parent?**

A: 30 child bags per parent bag.

**Q: Can one child be linked to multiple parents?**

A: No. One child bag can only link to one parent at a time.

### Bills

**Q: Who can create bills?**

A: Only Billers can create and edit bills. Dispatchers can view bills.

**Q: Can I delete a bill?**

A: Only Administrators can delete bills. Contact your admin if needed.

**Q: What's the difference between "Actual" and "Expected" weight?**

A: 
- **Actual**: Real weight based on scanned children (1kg per child)
- **Expected**: Full capacity weight (30kg per parent bag)
- **Variance**: Difference (shows under/over capacity)

**Q: Can I edit a bill after creation?**

A: Yes (Billers only). Click Edit Bill → Make changes → Save.

### Permissions

**Q: Why can't I see other dispatch areas?**

A: Dispatchers only see their assigned area. Billers see all areas.

**Q: How do I get access to bill management?**

A: Contact your administrator to upgrade your role from Dispatcher to Biller.

**Q: What can Dispatchers do?**

A: Scan bags, link children to parents, view bags/bills in their dispatch area.

**Q: What can Billers do?**

A: Everything Dispatchers can do, PLUS create/edit bills, access all areas, generate reports.

### Technical

**Q: What if the system is slow?**

A: 
1. Refresh page
2. Clear browser cache
3. Check internet connection
4. Contact admin if persistent

**Q: How long do sessions last?**

A: 1 hour maximum, or 30 minutes of inactivity. You'll need to login again after timeout.

**Q: Is my data saved automatically?**

A: Yes! Scans and bill changes save immediately. No "Save" button needed.

**Q: What if I lose internet connection?**

A: Current work may be lost. Refresh page when connection restored. System requires stable internet.

### Best Practices

**Q: When should I create a bill?**

A: Create bills before or during scanning. Link parent bags as you complete them.

**Q: How often should I generate reports?**

A: Daily scan reports recommended. Bill summaries at end of each shift or day.

**Q: Should I scan all children before moving to next parent?**

A: Yes! Complete one parent-children set before starting another. This prevents linking errors.

**Q: What if physical count doesn't match system count?**

A: 
1. Recount physical bags
2. Check system for duplicates
3. Rescan if needed
4. Contact admin if discrepancy persists

---

## Need Help?

### Support Resources

**In-App Help**:
- Click "?" icon in navigation
- Tooltips on hover (hover over fields)

**Contact Administrator**:
- Email: [Admin Email]
- Phone: [Admin Phone]
- Available: [Hours]

**Training Materials**:
- Video tutorials: [Link]
- Quick reference guide: [Link]
- FAQ updates: [Link]

---

## Related Documentation

- [Admin Guide](ADMIN_GUIDE_TROUBLESHOOTING.md) - For administrators
- [Operational Runbook](OPERATIONAL_RUNBOOK.md) - Technical operations
- [Feature Documentation](FEATURES.md) - System capabilities

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | November 2025 | Initial user guide for dispatchers and billers |

---

**Thank you for using TraitorTrack!** 🎯

Your efficient scanning and accurate bill management help keep operations running smoothly.

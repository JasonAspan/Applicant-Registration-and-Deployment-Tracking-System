# Gender Field Not Reflecting on Dashboard

**Issue**: Applicant form has gender select, but doesn't save to DB or show on dashboard.

**Root Cause**:
- Missing `gender` column in Applicant model.
- routes_applicant.py doesn't process `request.form['gender']`.
- dashboard.html expects it.

**Plan**:
1. Add `gender` to models.py Applicant.
2. Update routes_applicant.py to save gender.
3. Restart app → DB migrates.
4. Test: Submit form → Check dashboard column.

**Status**: Pending implementation.

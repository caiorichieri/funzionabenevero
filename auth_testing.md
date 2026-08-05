# Auth Testing Playbook

Focused checklist for this bug verification:

1. Verify auth seed credentials from `/app/memory/test_credentials.md`.
2. Log in via `/api/auth/login` and confirm cookies/user response for admin and therapist when active.
3. Confirm suspended/inactive users are rejected by `/api/auth/login` with HTTP 403 and `Account disattivato`.
4. Confirm reactivation restores normal therapist login.
5. Confirm UI API calls use credentials/cookies and protected admin actions are admin-only.
# JobQ Backend (Django)

This Django project powers the REST API for the JobQ application. It is designed to work alongside the React/Vite frontend located at `../`.

## Setup

1. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run migrations and create a superuser:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. (Optional) load initial data or create subscription plans via admin interface.

5. Start the development server:
   ```bash
   python manage.py runserver 9090
   ```

The API will be available at `http://localhost:9090/api/v1/`.

## Endpoints

The backend exposes the following major routes:

- **Authentication**
  - `POST /api/v1/auth/register/`
  - `POST /api/v1/auth/login/` (username or email + password)
  - `POST /api/v1/auth/logout/`
  - `POST /api/v1/auth/refresh/` (token refresh)
  - `GET/PUT /api/v1/auth/me/`
  - `POST /api/v1/auth/delete/` (delete account with password confirmation)
  - `POST /api/v1/auth/password-reset/request/` (send reset email)
  - `POST /api/v1/auth/password-reset/verify/` (verify reset token)
  - `POST /api/v1/auth/password-reset/` (reset password with token)
  - `POST /api/v1/auth/google/` & `/auth/linkedin/` (OAuth flows)

- **Jobs & Companies**
  - `/api/v1/jobs/` (list, create, retrieve, update, delete)
  - `/api/v1/companies/`
  - `/api/v1/jobs/extract/` & related status/result checks

- **Applications**
  - `/api/v1/applications/` plus stats and status-history endpoints

- **Notifications**
  - `/api/v1/notifications/`
  - `POST /api/v1/notifications/<id>/read/`

- **Profiles**
  - `/api/v1/profiles/` and nested operations for skills, experiences, education, certifications, resumes (upload & list)

- **Subscriptions**
  - `/api/v1/subscription/` plus upgrade, cancel, resume, payment methods, invoices

The frontend service modules in `src/services` are already set up to call these routes.

## Media files

Uploaded resumes are stored under `media/resumes/`. In development, Django serves media automatically when `DEBUG=True`.

## CORS

CORS is permitted from any origin by default (`CORS_ALLOW_ALL_ORIGINS = True`). Adjust in production.

## Email Configuration

Password reset emails are sent using Django's email backend. By default, emails are printed to the console in development.

In production, configure email via environment variables:

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@jobq.com
FRONTEND_URL=https://jobq.example.com
```

Password reset tokens expire after 1 hour and are stored in the database. Users can request a new token at any time.

## Notes

* This is a minimal implementation to satisfy the frontend requirements. Some endpoints (e.g. payment, social login) are stubbed and meant to be replaced with real logic.
* **AI extraction** currently uses OpenAI's ChatGPT API. To enable, set `OPENAI_API_KEY` in your environment. If the key is missing the server will fall back to a simple placeholder extractor.
* **Password reset** requires email configuration. For development, console backend prints emails to stdout.

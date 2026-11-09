# Portfolio backend

A small Flask API for the portfolio contact form. It validates messages, saves them to SQLite,
and emails you a notification.

## Endpoints
- `POST /api/contact` with JSON `{name, email, message}`. Limited to 5 requests per hour per IP.
- `GET /api/health` returns `{"status":"ok"}`.
- `GET /api/messages` lists saved messages. Needs the header `Authorization: Bearer <ADMIN_TOKEN>`.

## Run locally
```
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then edit .env
python app.py
```
Test it:
```
curl -X POST http://localhost:5000/api/contact -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@example.com","message":"Hello there"}'
```

## Gmail setup
Turn on 2-step verification for your Google account, then create an App Password
(Google Account > Security > App passwords). Put it in `SMTP_PASS`. Do not use your normal password.

## Deploy (for example on Render)
1. Push this folder to a GitHub repository.
2. Create a new Web Service on render.com from the repository.
3. Build command: `pip install -r requirements.txt`. Start command: `gunicorn app:app`.
4. Add the variables from `.env.example` in the dashboard. Set `ALLOWED_ORIGINS` to your site's address.
5. Copy the service URL, for example `https://your-app.onrender.com`.

Free hosts may erase the SQLite file when the service restarts. Emails still arrive, but for permanent
storage use a persistent disk or a hosted database.

## Connect the portfolio
In `portfolio.html`, set `var API_URL=''` to `'https://your-app.onrender.com/api/contact'`
and host the HTML on your own site (Netlify, GitHub Pages, Vercel). While `API_URL` is empty the form opens the visitor's email app instead.

# TutorAZ MVP

All-in-one tutor platform for Azerbaijan — tutor profiles, student search, group management.

## Stack

- **Backend**: Flask 3 + SQLAlchemy + Flask-Migrate
- **DB**: PostgreSQL (SQLite for local dev)
- **Frontend**: Jinja2 templates + Tailwind CSS (CDN)
- **Deploy**: Render.com
- **CI/CD**: GitHub Actions

## MVP Features (ICE top 3)

1. **Tutor profile creation** — tutors build public profiles with subjects, bio, pricing, phone, avatar
2. **Student search & discovery** — filter by subject, format (online/in-person), city
3. **Group creation** — tutors create groups with weekly schedule slots, students join via invite codes

## Course marketplace (Phase 2)

Tutors can package recorded lessons into paid or free courses:
- Course → Sections (e.g. "Optics", "Electromagnetism") → Lessons (video + optional homework/answer key)
- Students browse courses separately from tutor search, buy via Stripe Checkout (test mode)
- Payouts via **Stripe Connect Express** — platform takes a configurable % fee, rest goes straight to tutor's connected account
- Bank details are never stored by us — Stripe's hosted onboarding handles that

### ⚠️ Critical: video storage before going live

Course videos currently save to local disk (`app/static/uploads/`) for local development. **This will NOT work on Render or any host with ephemeral disk** — uploaded videos disappear on every redeploy/restart. Before launching:

1. Create an AWS S3 bucket + CloudFront distribution (or use Cloudflare R2/Stream as a cheaper alternative)
2. Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET`, `AWS_CLOUDFRONT_DOMAIN` env vars
3. Edit `app/storage.py` — the `save_file()`/`delete_file()` functions have the S3 swap-in code commented right above them

Until that's done, treat course video upload as **demo-only** — good enough to show the flow at Demo Day, not production-safe.

## Stripe test mode setup

1. Create a free account at [stripe.com](https://stripe.com) (no business verification needed for test mode)
2. Dashboard → Developers → API keys → copy the **test** publishable + secret keys
3. Add them to `.env` locally, and to Render's environment variables in production
4. Test card for checkout: `4242 4242 4242 4242`, any future expiry, any CVC
5. For Stripe Connect testing, tutor onboarding uses Stripe's test-mode hosted form — no real bank account needed

## Local Setup

```bash
# 1. Clone & install
git clone <repo>
cd tutoraz
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env → set DATABASE_URL (or leave blank for SQLite)

# 3. Database
flask db init       # first time only
flask db migrate -m "initial"
flask db upgrade

# 4. Run
python run.py
# → http://localhost:5000
```

## Deploy to Render

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your repo — Render reads `render.yaml` automatically
4. Set `SECRET_KEY` in Render dashboard (or it auto-generates)
5. Deploy → done ✓

## Project Structure

```
tutoraz/
├── app/
│   ├── __init__.py          # App factory
│   ├── models/
│   │   ├── user.py          # User (tutor + student)
│   │   ├── tutor.py         # TutorProfile, Subject
│   │   └── group.py         # Group, GroupMember
│   ├── routes/
│   │   ├── auth.py          # Register / Login / Logout
│   │   ├── main.py          # Landing + Dashboard
│   │   ├── tutor.py         # Profile edit + public view
│   │   ├── student.py       # Search
│   │   └── groups.py        # Group CRUD + join
│   └── templates/           # Jinja2 templates
├── tests/
├── migrations/
├── render.yaml              # Render deployment config
├── gunicorn.conf.py
├── requirements.txt
└── run.py
```

## Future (Anti-Roadmap)

When validated, add in order:
- Rating & review system
- Lesson scheduling
- In-app messaging
- File sharing / homework
- Payment integration (Stripe / local gateway)
- Verified DIM results
- Mobile app (Flutter)

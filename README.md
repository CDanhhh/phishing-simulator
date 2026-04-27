# Phishing Awareness Simulator

A tool to send simulated phishing emails and track user responses for security awareness training.

## Setup

### 1. Install Dependencies

```bash
cd phishing-simulator
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# SendGrid (free tier: 100 emails/day)
SENDGRID_API_KEY=SG.your-key-here
FROM_EMAIL=security@yourcompany.com
FROM_NAME=IT Security Team

# PostgreSQL Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=phishing_simulator
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password

# Application URL (for tracking links)
BASE_URL=https://your-domain.com
```

### 3. Set Up PostgreSQL Database

```bash
# Create database
psql -U postgres
CREATE DATABASE phishing_simulator;
\q
```

### 4. Initialize Database

```bash
flask init-db
```

### 5. Run the Application

```bash
python app.py
```

Access the landing page (static root): http://localhost:5000/

Access the Flask-rendered dashboard: http://localhost:5000/dashboard

Note: The repository now contains a static `index.html` at the project root that serves as a small landing page (logo + button). The dashboard template formerly named `templates/index.html` has been renamed to `templates/dashboard.html` and is served by Flask at `/dashboard`.

## Usage

### 1. Add Recipients
- Go to **Recipients** → **Add Recipient**
- Or bulk import via CSV (format: `email,name,department`)

### 2. Create Campaign
- Go to **New Campaign**
- Choose template (Password Reset, Invoice, Shared File)
- Set email subject

### 3. Send Campaign
- Click **Send** on the campaign page
- Emails are sent via SendGrid
- Clicks are tracked automatically

### 4. View Results
- Dashboard shows overall click rates
- Campaign detail shows individual click logs

## Email Templates

| Template | Scenario | Psychological Trigger |
|----------|----------|---------------------|
| Password Reset | Account security alert | Urgency, fear |
| Invoice | Billing notification | Curiosity, concern |
| Shared File | Document shared with you | Trust, expectation |

## Adding Custom Templates

Edit the `get_email_template()` function in `app.py` to add your own templates.

## Ethical Guidelines

- Only use with proper authorization
- Disclose phishing simulations in company security policy
- Track results for training purposes only
- Provide educational feedback to users who click

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from datetime import datetime
from config import Config
from models import db, Recipient, Campaign, ClickLog
from email_service import EmailService
import os

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
email_service = EmailService()


@app.after_request
def set_csp(response):
    csp = (
        "default-src 'self'; "
        "script-src 'self' https://static.cloudflareinsights.com; "
        "connect-src 'self' https://static.cloudflareinsights.com; "
        "img-src 'self' data: https://justinsec.me https://static.cloudflareinsights.com; "
        "style-src 'self' 'unsafe-inline';"
    )
    response.headers['Content-Security-Policy'] = csp
    return response

def init_db():
    db.create_all()

@app.cli.command("init-db")
def init_db_command():
    init_db()
    print("Database initialized!")

@app.route('/')
def root():
    # Serve the static landing page at the repository root (`index.html`).
    return send_from_directory(os.path.dirname(__file__), 'index.html')


@app.route('/dashboard')
def dashboard():
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    recipients_count = Recipient.query.count()
    total_clicks = ClickLog.query.filter(ClickLog.clicked_at.isnot(None)).count()
    total_sent = ClickLog.query.filter(ClickLog.email_sent_at.isnot(None)).count()
    
    stats = {
        'campaigns': len(campaigns),
        'recipients': recipients_count,
        'total_sent': total_sent,
        'total_clicks': total_clicks,
        'click_rate': round((total_clicks / total_sent * 100), 2) if total_sent > 0 else 0
    }
    
    return render_template('dashboard.html', campaigns=campaigns, stats=stats)

@app.route('/campaigns/new', methods=['GET', 'POST'])
def new_campaign():
    if request.method == 'POST':
        campaign = Campaign(
            name=request.form['name'],
            template_name=request.form['template'],
            subject=request.form['subject'],
            description=request.form.get('description', '')
        )
        db.session.add(campaign)
        db.session.commit()
        flash(f'Campaign "{campaign.name}" created!', 'success')
        return redirect(url_for('campaign_detail', campaign_id=campaign.id))
    return render_template('campaign_form.html', action='Create')

@app.route('/campaigns/<int:campaign_id>')
def campaign_detail(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    click_logs = ClickLog.query.filter_by(campaign_id=campaign_id).all()
    return render_template('campaign_detail.html', campaign=campaign, click_logs=click_logs)

@app.route('/campaigns/<int:campaign_id>/send', methods=['POST'])
def send_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    recipients = Recipient.query.all()
    
    if not recipients:
        flash('No recipients to send to!', 'danger')
        return redirect(url_for('campaign_detail', campaign_id=campaign_id))
    
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        flash('SMTP not configured!', 'danger')
        return redirect(url_for('campaign_detail', campaign_id=campaign_id))
    
    template_content = get_email_template(campaign.template_name)
    sent_count = 0
    
    for recipient in recipients:
        token = ClickLog.generate_token()
        click_log = ClickLog(
            token=token,
            recipient_id=recipient.id,
            campaign_id=campaign.id
        )
        db.session.add(click_log)
        
        tracking_link = f"{Config.BASE_URL}/track/{token}"
        html_content = template_content.format(
            name=recipient.name or 'User',
            tracking_link=tracking_link,
            year=datetime.now().year
        )
        
        status_code, _ = email_service.send_email(recipient.email, campaign.subject, html_content)
        
        if status_code == 202 or status_code == 200:
            click_log.email_sent_at = datetime.utcnow()
            sent_count += 1
    
    campaign.status = 'sent'
    campaign.sent_at = datetime.utcnow()
    db.session.commit()
    
    flash(f'Successfully sent {sent_count}/{len(recipients)} emails!', 'success')
    return redirect(url_for('campaign_detail', campaign_id=campaign_id))

@app.route('/recipients')
def recipients():
    recipients_list = Recipient.query.order_by(Recipient.created_at.desc()).all()
    return render_template('recipients.html', recipients=recipients_list)

@app.route('/recipients/add', methods=['GET', 'POST'])
def add_recipient():
    if request.method == 'POST':
        email = request.form['email']
        if Recipient.query.filter_by(email=email).first():
            flash(f'Recipient {email} already exists!', 'warning')
            return redirect(url_for('add_recipient'))
        
        recipient = Recipient(
            email=email,
            name=request.form.get('name', ''),
            department=request.form.get('department', '')
        )
        db.session.add(recipient)
        db.session.commit()
        flash(f'Recipient {email} added!', 'success')
        return redirect(url_for('recipients'))
    return render_template('recipient_form.html')

@app.route('/recipients/import', methods=['POST'])
def import_recipients():
    if 'file' not in request.files:
        flash('No file uploaded!', 'danger')
        return redirect(url_for('recipients'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected!', 'danger')
        return redirect(url_for('recipients'))
    
    added = 0
    skipped = 0
    
    for line in file.read().decode('utf-8').strip().split('\n'):
        parts = line.strip().split(',')
        if len(parts) >= 1 and parts[0]:
            email = parts[0].strip()
            name = parts[1].strip() if len(parts) > 1 else ''
            department = parts[2].strip() if len(parts) > 2 else ''
            
            if not Recipient.query.filter_by(email=email).first():
                recipient = Recipient(email=email, name=name, department=department)
                db.session.add(recipient)
                added += 1
            else:
                skipped += 1
    
    db.session.commit()
    flash(f'Imported {added} recipients ({skipped} skipped)', 'success')
    return redirect(url_for('recipients'))

@app.route('/track/<token>')
def track_click(token):
    click_log = ClickLog.query.filter_by(token=token).first()
    
    if not click_log:
        return render_template('landing_page.html', 
                             caught=False, 
                             message="Link not found or expired.")
    
    if click_log.clicked_at:
        return render_template('landing_page.html',
                             caught=False,
                             message="You already clicked this link!")
    
    click_log.clicked_at = datetime.utcnow()
    click_log.ip_address = request.remote_addr
    click_log.user_agent = request.headers.get('User-Agent', '')
    db.session.commit()
    
    campaign = click_log.campaign
    recipient = click_log.recipient
    
    return render_template('landing_page.html',
                         caught=True,
                         recipient_name=recipient.name,
                         campaign_name=campaign.name)

@app.route('/api/campaigns/<int:campaign_id>/stats')
def campaign_stats(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    return jsonify({
        'name': campaign.name,
        'status': campaign.status,
        'total_sent': campaign.get_total_sent(),
        'total_clicks': campaign.get_total_clicks(),
        'click_rate': campaign.get_click_rate()
    })

@app.route('/api/campaigns/<int:campaign_id>/delete', methods=['POST'])
def delete_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    ClickLog.query.filter_by(campaign_id=campaign_id).delete()
    db.session.delete(campaign)
    db.session.commit()
    flash(f'Campaign deleted!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/recipients/<int:recipient_id>/delete', methods=['POST'])
def delete_recipient(recipient_id):
    recipient = Recipient.query.get_or_404(recipient_id)
    ClickLog.query.filter_by(recipient_id=recipient_id).delete()
    db.session.delete(recipient)
    db.session.commit()
    flash(f'Recipient deleted!', 'success')
    return redirect(url_for('recipients'))

def get_email_template(template_name):
    templates = {
        'password_reset': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ background: #d32f2f; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; margin: -30px -30px 20px -30px; }}
        .button {{ display: inline-block; background: #1976d2; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
        .footer {{ color: #666; font-size: 12px; margin-top: 20px; border-top: 1px solid #eee; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Security Alert</h1>
        </div>
        <p>Hi {name},</p>
        <p>We detected suspicious activity on your account. Your password will expire in <strong>24 hours</strong>.</p>
        <p>To prevent unauthorized access, please verify your identity immediately:</p>
        <p style="text-align: center;">
            <a href="{tracking_link}" class="button">Verify My Account</a>
        </p>
        <p>If you don't verify within 24 hours, your account will be locked.</p>
        <div class="footer">
            <p>IT Security Team<br>
            This is an automated message. Do not reply.</p>
        </div>
    </div>
</body>
</html>''',
        
        'invoice': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ background: #2e7d32; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; margin: -30px -30px 20px -30px; }}
        .button {{ display: inline-block; background: #2e7d32; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
        .footer {{ color: #666; font-size: 12px; margin-top: 20px; border-top: 1px solid #eee; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📄 Invoice Notification</h1>
        </div>
        <p>Hi {name},</p>
        <p>Your monthly invoice #{year}0847 is ready for review.</p>
        <p><strong>Amount Due:</strong> $1,847.00</p>
        <p><strong>Due Date:</strong> Immediate</p>
        <p style="text-align: center;">
            <a href="{tracking_link}" class="button">View Invoice</a>
        </p>
        <p>Please review and process payment within 48 hours to avoid service interruption.</p>
        <div class="footer">
            <p>Accounting Department<br>
            Questions? Contact billing@company.com</p>
        </div>
    </div>
</body>
</html>''',
        
        'shared_file': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ background: #7b1fa2; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; margin: -30px -30px 20px -30px; }}
        .button {{ display: inline-block; background: #7b1fa2; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
        .footer {{ color: #666; font-size: 12px; margin-top: 20px; border-top: 1px solid #eee; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📁 File Shared With You</h1>
        </div>
        <p>Hi {name},</p>
        <p><strong>HR Department</strong> shared a file with you:</p>
        <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 15px 0;">
            <strong>Q4_Salary_Report_{year}.xlsx</strong><br>
            <span style="color: #666;">Excel Spreadsheet • 245 KB</span>
        </div>
        <p style="text-align: center;">
            <a href="{tracking_link}" class="button">Open Document</a>
        </p>
        <p>This file will be available for 7 days.</p>
        <div class="footer">
            <p>Powered by SharePoint<br>
            <a href="#">Unsubscribe</a> | <a href="#">View in browser</a></p>
        </div>
    </div>
</body>
</html>'''
    }
    return templates.get(template_name, templates['password_reset'])

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

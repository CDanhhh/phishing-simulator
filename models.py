from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Recipient(db.Model):
    __tablename__ = 'recipients'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255))
    department = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    click_logs = db.relationship('ClickLog', backref='recipient', lazy=True)
    
    def __repr__(self):
        return f'<Recipient {self.email}>'

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    template_name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    clicks = db.relationship('ClickLog', backref='campaign', lazy=True)
    
    def get_total_sent(self):
        return len([c for c in self.clicks if c.email_sent_at is not None])
    
    def get_total_clicks(self):
        return len([c for c in self.clicks if c.clicked_at is not None])
    
    def get_click_rate(self):
        sent = self.get_total_sent()
        if sent == 0:
            return 0
        return round((self.get_total_clicks() / sent) * 100, 2)
    
    def __repr__(self):
        return f'<Campaign {self.name}>'

class ClickLog(db.Model):
    __tablename__ = 'click_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, default=uuid.uuid4().hex)
    recipient_id = db.Column(db.Integer, db.ForeignKey('recipients.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    email_sent_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    
    @staticmethod
    def generate_token():
        return uuid.uuid4().hex
    
    def __repr__(self):
        return f'<ClickLog {self.token}>'

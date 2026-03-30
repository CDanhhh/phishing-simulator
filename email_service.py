import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from config import Config

class EmailService:
    def __init__(self):
        self.smtp_host = Config.SMTP_HOST
        self.smtp_port = Config.SMTP_PORT
        self.smtp_user = Config.SMTP_USER
        self.smtp_password = Config.SMTP_PASSWORD
        self.from_email = Config.FROM_EMAIL
        self.from_name = Config.FROM_NAME
    
    def send_email(self, to_email, subject, html_content):
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8')
        
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, [to_email], msg.as_string())
            return 200, "Email sent successfully"
        except smtplib.SMTPException as e:
            print(f"SMTP Error sending email: {e}")
            return 500, str(e)
        except Exception as e:
            print(f"Error sending email: {e}")
            return 500, str(e)
    
    def send_bulk(self, recipients_data):
        results = []
        for recipient in recipients_data:
            status_code, response = self.send_email(
                recipient['email'],
                recipient['subject'],
                recipient['html_content']
            )
            results.append({
                'email': recipient['email'],
                'status': status_code,
                'success': status_code == 200
            })
        return results

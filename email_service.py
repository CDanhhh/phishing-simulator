import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from config import Config

class EmailService:
    def __init__(self):
        self.sg = sendgrid.SendGridAPIClient(api_key=Config.SENDGRID_API_KEY)
        self.from_email = Config.FROM_EMAIL
        self.from_name = Config.FROM_NAME
    
    def send_email(self, to_email, subject, html_content):
        from_email = Email(self.from_email, self.from_name)
        to_email = To(to_email)
        content = Content("text/html", html_content)
        mail = Mail(from_email, to_email, subject, content)
        
        try:
            response = self.sg.client.mail.send.post(request_body=mail.get())
            return response.status_code, response.body
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
                'success': status_code == 202 or status_code == 200
            })
        return results

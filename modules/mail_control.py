import webbrowser
import urllib.parse

class MailControl:
    def __init__(self):
        pass

    def send_email(self, To_Recipient, Subject="", Body=""):
        """Open the default Windows email client with a mailto link."""
        recipient = To_Recipient if To_Recipient else ""
        subject = Subject if Subject else ""
        body = Body if Body else ""
        
        # Build mailto URI
        mailto_link = f"mailto:{recipient}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        
        try:
            webbrowser.open(mailto_link)
            print("Opening mail client...")
            return True
        except Exception as e:
            print(f"Error opening mail: {e}")
            return False

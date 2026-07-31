class Notifier:
    """Basic notification service."""
    def send_email(self, recipient, subject, body):
        return {'success':True,'channel':'email','recipient':recipient,'subject':subject}
    def send_telegram(self, chat_id, message):
        return {'success':True,'channel':'telegram','chat_id':chat_id}
    def send(self,*args,**kwargs):
        return {'success':True}

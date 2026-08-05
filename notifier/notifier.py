"""Notification services for matched job alerts."""
import json,smtplib
from email.message import EmailMessage
from urllib import error,parse,request
class Notifier:
    def __init__(self,smtp_host=None,smtp_port=587,smtp_username=None,smtp_password=None,smtp_sender=None,telegram_bot_token=None,timeout=20):self.smtp_host=smtp_host;self.smtp_port=int(smtp_port);self.smtp_username=smtp_username;self.smtp_password=smtp_password;self.smtp_sender=smtp_sender or smtp_username;self.telegram_bot_token=telegram_bot_token;self.timeout=timeout
    def send_email(self,recipient,subject,body):
        if not self.smtp_host or not self.smtp_sender:raise ValueError("SMTP host and sender must be configured")
        if not recipient:raise ValueError("Email recipient is required")
        message=EmailMessage();message["From"]=self.smtp_sender;message["To"]=recipient;message["Subject"]=subject;message.set_content(body)
        with smtplib.SMTP(self.smtp_host,self.smtp_port,timeout=self.timeout) as smtp:
            smtp.ehlo();smtp.starttls();smtp.ehlo()
            if self.smtp_username and self.smtp_password:smtp.login(self.smtp_username,self.smtp_password)
            smtp.send_message(message)
        return {"success":True,"channel":"email","recipient":recipient,"subject":subject}
    def send_telegram(self,chat_id,message):
        if not self.telegram_bot_token:raise ValueError("Telegram bot token must be configured")
        if not chat_id:raise ValueError("Telegram chat_id is required")
        endpoint=f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage";payload=parse.urlencode({"chat_id":str(chat_id),"text":message,"disable_web_page_preview":"true"}).encode("utf-8");req=request.Request(endpoint,data=payload,method="POST")
        try:
            with request.urlopen(req,timeout=self.timeout) as response:data=json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:raise RuntimeError(f"Telegram notification failed: {exc}") from exc
        if not data.get("ok"):raise RuntimeError(f"Telegram notification failed: {data.get('description','unknown error')}")
        return {"success":True,"channel":"telegram","chat_id":str(chat_id),"message_id":(data.get("result") or {}).get("message_id")}
    def send(self,channel,**kwargs):
        normalized=str(channel or "").strip().lower()
        if normalized=="email":return self.send_email(kwargs.get("recipient",""),kwargs.get("subject","JobHunter AI Alert"),kwargs.get("body",kwargs.get("message","")))
        if normalized=="telegram":return self.send_telegram(kwargs.get("chat_id",""),kwargs.get("message",kwargs.get("body","")))
        raise ValueError(f"Unsupported notification channel: {channel!r}")
    @staticmethod
    def format_job_alert(job,match=None,priority=None,priority_score=None):
        match=match or {};get=job.get if isinstance(job,dict) else lambda key,default="":getattr(job,key,default);lines=[f"{get('title','New Job')} — {get('company','')}".strip(" —")]
        if priority:lines.append(f"Priority: {priority}"+(f" ({float(priority_score):.0f}/100)" if priority_score is not None else ""))
        location=get("location","")
        if location:lines.append(f"Location: {location}")
        if "score" in match:lines.append(f"Match: {float(match['score']):.0f}%")
        missing=match.get("missing_skills") or []
        if missing:lines.append(f"Missing skills: {', '.join(missing)}")
        apply_url=get("apply_url","")
        if apply_url:lines.append(f"Apply: {apply_url}")
        return "\n".join(lines)

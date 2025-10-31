#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\tools\email_sender_tools\processor.py JUMLAH BARIS 122 
#######################################################################

import smtplib
import os
import tempfile
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from flowork_kernel.api_contract import BaseModule, IExecutable, IDataPreviewer
from flowork_kernel.utils.payload_helper import get_nested_value
class EmailSenderModule(BaseModule, IExecutable, IDataPreviewer):
    """
    (REMASTERED V6) Sends an email based on explicit instructions from the payload,
    and can now resolve payload variables within attachment content for maximum efficiency.
    """
    TIER = "basic"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.variable_manager = self.kernel.get_service("variable_manager")
    def execute(self, payload: dict, config: dict, status_updater, mode='EXECUTE', **kwargs): # ADD CODE
        if not self.variable_manager:
            return {"payload": {"data": {"error": "VariableManager service is not available."}}, "output_name": "error"}
        smtp_host = self.variable_manager.get_variable("SMTP_HOST")
        smtp_port = self.variable_manager.get_variable("SMTP_PORT")
        email_address = self.variable_manager.get_variable("EMAIL_ADDRESS")
        email_password = self.variable_manager.get_variable("EMAIL_PASSWORD")
        if not all([smtp_host, smtp_port, email_address, email_password]):
            return {"payload": {"data": {"error": "SMTP credentials are not fully configured in Settings -> Variable Management."}}, "output_name": "error"}
        try:
            smtp_port = int(smtp_port)
        except (ValueError, TypeError):
            return {"payload": {"data": {"error": "SMTP_PORT must be a valid number."}}, "output_name": "error"}
        payload_data = payload.get('data', {})
        recipient_to = payload_data.get('recipient_to') or payload_data.get('to') or payload_data.get('recipient') or config.get('recipient_to')
        subject = payload_data.get('subject') or config.get('subject')
        body = payload_data.get('body') or config.get('body')
        if not recipient_to or not subject or not body:
            error_msg = "Required fields (recipient, subject, body) are empty in both payload and config."
            self.logger(error_msg, "ERROR")
            status_updater(error_msg, "ERROR")
            if 'data' not in payload: payload['data'] = {}
            payload['data']['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        status_updater(f"Preparing to send email to {recipient_to}...", "INFO")
        msg = MIMEMultipart()
        msg['From'] = email_address
        msg['To'] = recipient_to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        attachments = payload_data.get('attachments', [])
        if isinstance(attachments, list):
            for item in attachments:
                if isinstance(item, str) and os.path.isfile(item):
                    self._attach_file(msg, item)
                    status_updater(f"Attaching file: {os.path.basename(item)}", "INFO")
                elif isinstance(item, dict) and 'filename' in item and 'content' in item:
                    content_value = item.get('content', '')
                    placeholder_match = re.match(r"\{\{([\w\.]+)\}\}", str(content_value))
                    if placeholder_match:
                        variable_path = placeholder_match.group(1)
                        self.logger(f"Found payload variable '{variable_path}' in attachment content.", "DEBUG")
                        content_from_payload = get_nested_value(payload, variable_path)
                        if content_from_payload:
                            self._create_and_attach_temp_file(msg, item['filename'], str(content_from_payload))
                            status_updater(f"Creating and attaching '{item['filename']}' from payload.", "INFO")
                        else:
                             self.logger(f"Variable '{variable_path}' not found in payload. Skipping attachment.", "WARN")
                    elif content_value:
                        self._create_and_attach_temp_file(msg, item['filename'], str(content_value))
                        status_updater(f"Creating and attaching: {item['filename']}", "INFO")
                    else:
                        self.logger(f"Skipping attachment '{item['filename']}' because its content is empty.", "WARN")
                else:
                    self.logger(f"Could not process attachment item: {item}. It is not a valid path or a valid content object.", "WARN")
        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(email_address, email_password)
                server.send_message(msg)
            status_updater("Email sent successfully.", "SUCCESS")
            self.logger(f"Email successfully sent to {recipient_to}", "SUCCESS")
            if 'data' not in payload: payload['data'] = {}
            payload['data']['email_status'] = 'Sent successfully'
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            error_msg = f"Failed to send email: {e}"
            self.logger(error_msg, "ERROR")
            if 'data' not in payload: payload['data'] = {}
            payload['data']['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
    def _attach_file(self, msg, file_path):
        try:
            with open(file_path, "rb") as attachment_file:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment_file.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {os.path.basename(file_path)}",
            )
            msg.attach(part)
            self.logger(f"Successfully attached file: {os.path.basename(file_path)}", "INFO")
        except Exception as e:
            self.logger(f"Could not attach file '{file_path}': {e}", "WARN")
    def _create_and_attach_temp_file(self, msg, filename, content):
        try:
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=f"_{filename}", encoding='utf-8') as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            self._attach_file(msg, tmp_path)
            os.unlink(tmp_path)
        except Exception as e:
            self.logger(f"Could not create or attach temporary file '{filename}': {e}", "ERROR")
    def get_data_preview(self, config: dict):
        return [{'status': 'preview_not_available', 'reason': 'Email sending is a live action.'}]

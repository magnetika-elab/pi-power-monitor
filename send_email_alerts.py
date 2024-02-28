import os
import re
import sys
import time
import base64
import pickle
from premailer import transform
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import http.client as httplib



def have_internet():
    conn = httplib.HTTPSConnection("8.8.8.8", timeout=5)
    try:
        conn.request("HEAD", "/")
        return True
    except Exception:
        return False
    finally:
        conn.close()

def unsentAlerts():
    cwd = os.getcwd()
    alert_file_directory = os.path.join(cwd, 'Email_Alerts')
    if not os.path.isdir(alert_file_directory):
        os.mkdir(alert_file_directory)
    alert_files = [os.path.join(alert_file_directory, filename) for filename in os.listdir(alert_file_directory) if filename.endswith('.alert.txt')]
    return ((True if len(alert_files) > 0 else False), alert_files)

def getMailingList(testmode=False):
    mailing_list_file_path = os.path.join(os.getcwd(), f'mailing_list{"_testmode" if testmode else ""}.txt')
    if os.path.isfile(mailing_list_file_path):
        with open(mailing_list_file_path, 'r') as file:
            address_list = [
                line for line in file.read().split('\n') if ((line != '') and (not line.startswith('#')))
            ]
        #make sure regular email addresses are handled first in list
        address_list = [entry for entry in address_list if '@' in entry] + [entry for entry in address_list if '@' not in entry]
        return address_list
    else:
        with open(mailing_list_file_path, 'w') as file:
            file.write('')
        return []

def validateAddresses(address_list):
    sms_gateways = [
        'sms.alltelwireless.com', 'txt.att.net', 'sms.myboostmobile.com', 
        'mms.cricketwireless.net', 'mymetropcs.com', 'text.republicwireless.com', 
        'messaging.sprintpcs.com', 'tmomail.net', 'email.uscc.net', 'vtext.com', 'vmobl.com', 
    ]
    sms_gateways_canada = [ #unused for now
        'txt.bell.ca', 'text.mts.net', 'fido.ca', 'txt.freedommobile.ca', 'msg.telus.com', 
        'mobiletxt.ca', 'pcs.rogers.com', 'sms.sasktel.com', 'msg.telus.com'
    ]

    output = []
    for entry in address_list:
        if '@' in entry:           #if entry is an email adress
            output.append(entry)
        else:                      #assume it is a phone number if otherwise
            sanitized_entry = entry
            remove_characters = '() -+.'
            for remove_character in remove_characters:
                sanitized_entry = sanitized_entry.replace(remove_character, '')
            for gateway in sms_gateways:
                output.append(sanitized_entry + '@' + gateway)
    return output


def get_gmail_service():
    creds = None
    TOKEN_PATH = os.path.join(os.getcwd(), 'email_token.pickle')
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(os.getcwd(), 'client_secret_91846246009-qforo9v6g7421i8k1k4ltm1tbkoqq7b1.apps.googleusercontent.com.json'),  
                ['https://www.googleapis.com/auth/gmail.send']
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

def send_email(to, subject, body):
    service = get_gmail_service()
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    message.attach(MIMEText(body, 'html'))
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    retries = 0
    while retries <= 5:
        try:
            sent_message = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
            print(f'Message Id: {sent_message["id"]}')
            return True
        except Exception as error:
            print(f'An error occurred: {error}')
            retries += 1
            time.sleep(10 if retries == 3 else 1)
    return False


def handle_emails(recipient, email_subject, alert_text, testmode=False):
    email_subject = f'{"[TEST-ALERT]" if testmode else ""}{email_subject}'
    pattern = r'(?P<entry_valuename>.+)="(?P<entry_value>.+)"'
    results = re.findall(pattern, alert_text)
    alert_value_dict = dict((x, y) for x, y in results)
    email_style = '''
    <style>
        #tablestuff, table {
            color: lightgrey;
            background-color: black;
            display: inline-block;
        }
        table {
            font-family: arial, sans-serif;
            border-collapse: collapse;
        }
        th, td {
            border: 1px solid #444444;
            padding: 8px;
        }
        #left_col {
            width: 50%;
            text-align: right;
            padding-right: 16px; /* Adjust the right padding to visually center the header */
        }
        #right_col {
            width: 50%;
            text-align: left;
            padding-left: 16px; /* Adjust the left padding to visually center the header */
        }
        #power_event {
            text-align: center;
            padding-left: 16px; /* Adjust the left padding to visually center the header */
            padding-right: 16px; /* Adjust the right padding to visually center the header */
        }
    </style>
'''
    email_body = '''<!DOCTYPE html>
<html>'''+email_style+'''
        <body>
            <div id="tablestuff">
                <table>
                    <tr>
                        <th colspan="2" id="power_event">power event</th>
                    </tr>
                    <tr>
                      <td id="left_col">Event type</td>
                      <td id="right_col">{event_type}</td>
                    </tr>
                    <tr>
                      <td id="left_col">Event Occurrence Time</td>
                      <td id="right_col">{event_datetime}</td>
                    </tr>
                </table>
            </div>
        </body>
</html>'''.format(event_type = alert_value_dict['event_type'], event_datetime=alert_value_dict['event_datetime'])
    email_body = transform(email_body)
    #print(email_body)
    if isinstance(recipient, (list, tuple)):
        for address in recipient:
            print(f'Sending email to {address}')
            success = send_email(address, email_subject, email_body)
            if not success:
                print(f'Failed to send email to {address}')
            time.sleep(0.125) # Throttle sending
    elif isinstance(recipient, str):
        print(f'Sending email to {recipient}')
        success = send_email(recipient, email_subject, email_body)
        if not success:
            print(f'Failed to send email to {recipient}')




def sendAlerts(testmode=False):
    recipients = validateAddresses(
        getMailingList(testmode)
    )
    alert_files = unsentAlerts()[1]

    for alert_file_path in alert_files:
        alert_subject = os.path.splitext(os.path.basename(alert_file_path))[0]
        with open(alert_file_path, 'r') as file:
            alert_message = file.read()
        print(f'\n{alert_file_path}\n\t{alert_subject}\n\t\t{alert_message}\n')
        handle_emails(
            recipients,
            alert_subject,
            alert_message,
            testmode
        )
        try:
            os.rename(
                alert_file_path,
                alert_file_path.replace('.alert.txt','.alert.txt.old')
            )
        except:
            os.remove(alert_file_path)

    return


def main(testmode=False):
    if have_internet() and unsentAlerts()[0]:   #unsentAlerts() returns a tuple, the first item of which is a bool
        sendAlerts(testmode)
    exit()

if __name__ == '__main__':
    print(sys.argv)
    main(testmode=('--testmode' in sys.argv))
import os, sys, time, datetime
import RPi.GPIO as GPIO

def checkArgs():
    args = sys.argv
    if len(args) > 1:
        args = args[1:]
    return args

def directoryCheck():
    cwd = os.getcwd()
    alert_file_directory = os.path.join(cwd, 'Email_Alerts')
    if not os.path.isdir(alert_file_directory):
        os.mkdir(alert_file_directory)
    last_power_state_file_path = os.path.join(os.getcwd(), 'last_power_state.txt')
    if not os.path.isfile(last_power_state_file_path):
        with open(last_power_state_file_path, 'w') as file:
            file.write('1')

def checkGpio():
    time_at_call = datetime.datetime.now()
    power_indication_pin = 16 # physical pin 16   
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(power_indication_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # set power_indication_pin as an input with a pulldown resistor
    power_indication_pin_state =  GPIO.input(power_indication_pin)
    GPIO.cleanup()

    print(time_at_call, power_indication_pin_state)
    return (time_at_call, power_indication_pin_state)

def createAlert(alert_subject, alert_message):
    alert_file_directory = os.path.join(os.getcwd(), 'Email_Alerts')
    alert_file_name = alert_subject + '.alert.txt' if not alert_subject.endswith('.alert.txt') else alert_subject
    alert_file_path = os.path.join(alert_file_directory, alert_file_name)
    with open(alert_file_path, 'w') as alert_file:
        alert_file.write(alert_message)
    return

def log_status(status):
    last_power_state_file_path = os.path.join(os.getcwd(), 'last_power_state.txt')
    try:
        with open(last_power_state_file_path,'r') as file:
            last_state = int(file.read())
    except:
        last_state = None
        pass
    time_at_call, power_indication_pin_state = status
    if power_indication_pin_state != last_state:
        formatted_datetime  = time_at_call.strftime('%A, %B %d, %Y %I:%M %p')
        alert_subject = '[{0}]'.format(time_at_call.strftime("%Y%m%d%H%M%S")) + ('Power Loss' if power_indication_pin_state == 0 else 'Power Restored')
        alert_message = '''
event_datetime="{0}"
event_type="{1}"
'''.format(formatted_datetime, 'power loss' if power_indication_pin_state == 0 else 'power recovery')
        createAlert(
            alert_subject,
            alert_message
        )
    
    with open(last_power_state_file_path, 'w') as file:
        file.write(str(power_indication_pin_state))
    return

def main():
    directoryCheck()
    if checkArgs()[0] == 'cron':
        log_status(checkGpio())
    elif checkArgs()[0] == 'single':
        checkGpio()
    else:
        for i in range(120):
            checkGpio()
            time.sleep(1)
    exit()  

if __name__ == '__main__':
    main()
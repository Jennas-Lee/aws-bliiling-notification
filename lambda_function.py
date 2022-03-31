from calendar import month
import json
import boto3
import urllib3
from datetime import date, timedelta
from calendar import monthrange

def get_now_exchange():
    http = urllib3.PoolManager()
    exchange_url = 'http://fx.kebhana.com/FER1101M.web'
    request = http.request(
        'GET',
        exchange_url,
    )
    now_exchange = json.loads(request.data.decode('euc-kr').replace('\n', '').replace('\r', '').replace('\t', '').replace(' ', '').replace('varexView=', '').replace(',]}', ']}'))['리스트'][0]['현찰사실때']
    
    return now_exchange
    
def lambda_handler(event, context):
    today = date.today()
    month_later = date(today.year, today.month, monthrange(today.year, today.month)[1]) + timedelta(1)
    slack_url = '<YOUR SLACK INCOMING WEBHOOK URL>'
    payload = {
    	"blocks": [
    		{
    			"type": "header",
    			"text": {
    				"type": "plain_text",
    				"text": ""
    			}
    		},
    		{
    			"type": "section",
    			"text": {
    				"type": "mrkdwn",
    				"text": ""
    			}
    		},
    		{
    			"type": "section",
    			"text": {
    				"type": "plain_text",
    				"text": ""
    			}
    		},
    		{
    			"type": "divider"
    		},
    		{
    			"type": "section",
    			"text": {
    				"type": "mrkdwn",
    				"text": "*Top of the Billing*"
    			}
    		},
    		{
    			"type": "section",
    			"fields": []
    		}
    	]
    }

    client = boto3.client('ce')
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': str(today.strftime("%Y-%m-01")),
            'End': str(month_later)
        },
        Granularity='MONTHLY',
        Filter={
            'Dimensions':{
                'Key': 'LINKED_ACCOUNT',
                'Values': ['<YOUR AWS ACCOUNT ID>']
            }
        },
        GroupBy=[
            {
                "Type": "DIMENSION",
                "Key":"USAGE_TYPE"
            }
        ],
        Metrics=['UnblendedCost']
    )
    
    sum = 0.0
    new_groups = {}
    groups = response['ResultsByTime'][0]['Groups']
    max_length_resource_type = 0
    max_length_amount = 0
    for group in groups:
        resource_type = group['Keys'][0]
        amount = group['Metrics']['UnblendedCost']['Amount']
        
        if len(resource_type) > max_length_resource_type:
            max_length_resource_type = len(resource_type)
        
        if len(amount) > max_length_amount:
            max_length_amount = len(amount)
        
        sum += float(amount)
        
        if resource_type == 'NoUsageType':
            pass # TAX
        else:
            new_groups[resource_type] = amount
    
    new_groups = list(dict(sorted(new_groups.items(), key=lambda x: x[1], reverse=True)).items())
    
    for resource_type, amount in new_groups[:5]:
        resource_type_field = {"type": "plain_text", "text": resource_type}
        amount_field = {"type": "plain_text", "text": amount}
        payload['blocks'][5]['fields'].append(resource_type_field)
        payload['blocks'][5]['fields'].append(amount_field)
    
    response = response['ResultsByTime'][0]
    
    payload['blocks'][0]['text']['text'] = str(today) + ' Billing Report'
    payload['blocks'][1]['text']['text'] = '*' + response['TimePeriod']['Start'] + ' ~ ' + response['TimePeriod']['End'] + '*'
    payload['blocks'][2]['text']['text'] = \
        str(sum) + ' USD\n' + \
        str(sum * float(get_now_exchange())) + ' KRW\n' + \
        'Exchange Rate : ' + get_now_exchange()
    
    http = urllib3.PoolManager()
    request = http.request(
        'POST',
        slack_url,
        body=bytes(json.dumps(payload), encoding="UTF-8"),
    )
    
    return {
        'statusCode': 200,
    }
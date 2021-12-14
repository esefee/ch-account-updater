import os
import http.client
import json

#to do: flexibility around role ARN naming convention

api_key = os.environ.get('api_key')
external_id = os.environ.get('external_id')
friendly_name_prefix = os.environ.get('friendly_name_prefix')
arn_role_name = os.environ.get('arn_role_name')

def lambda_handler(event, context):
    def get_unconfigured_accounts(api_key):
        base_url = 'chapi.cloudhealthtech.com'
        query = '/api/search.json?api_version=2&name=AwsAccount&querystatus=\'Not-Configured\'&fields=owner_id'
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % api_key} 
        connection = http.client.HTTPSConnection(base_url)
        connection.request('GET', query, headers = headers)
        response =  json.loads(connection.getresponse().read().decode())
        connection.close()
        return response
    
    unconfigured_accounts = get_unconfigured_accounts(api_key)

    def update_account(api_key, ch_account_id, friendly_name, role_arn, external_id):
        base_url = 'chapi.cloudhealthtech.com'
        query = '/v1/aws_accounts/%s' % ch_account_id
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % api_key} 
        account_info = {
            "name": "%s" % friendly_name, 
            "authentication": {
                "protocol": "assume_role",
                "assume_role_arn": "%s" % role_arn,
                "assume_role_external_id": "%s" % external_id
                }
            }
        body = json.dumps(account_info)
        print(body)
        connection = http.client.HTTPSConnection(base_url)
        connection.request('PUT', url = query, body = body, headers = headers)
        response =  connection.getresponse()
        connection.close()
        return response
    
    for item in unconfigured_accounts:
        role_arn = 'arn:aws:iam::%s:role/%s' % (item['owner_id'], arn_role_name)
        friendly_name = friendly_name_prefix + " - " + str(item['owner_id'])
        print('\n',"--------------------------", '\n', 'Owner ID: ', item['owner_id'], ', CH Account ID: ', item['id'], ', Friendly Name: ', friendly_name)
        update_account(api_key, item['id'], friendly_name, role_arn, external_id)
    return event

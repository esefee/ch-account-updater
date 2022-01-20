# This function works by calling into CH and looking for unconfigured accounts and updating their configuration with a single common role name.
# this function is not aware of multiple organization structures and will attempt to configure any unconfigured account in your CH environment.
# for example: if you have multiple aws organizations, you will need to ensure all CH access roles in all linked accounts across all organizations use a common name.

import os
import http.client
import json

api_key = os.environ.get('api_key')
external_id = os.environ.get('external_id')
arn_role_name = "CloudHealth-Access"
client_api_id = os.environ.get('client_api_id')

def lambda_handler(event, context):
    def customer_check(client_api_id, api_key):
        if client_api_id == "Not a partner":
            return False
        else:
            base_url = 'chapi.cloudhealthtech.com'
            query = '/v1/customers/%s' % client_api_id
            headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % api_key}
            try:
                connection = http.client.HTTPSConnection(base_url)
                connection.request('GET', query, headers = headers)
                status = connection.getresponse().status
                connection.close()
                if status == 200:
                    return True
                else:
                    print('\n',"--------------------------", '\n', "Please check the client ID provided is correct, or that the customer account is active. \n")
                    return False
            except http.client.InvalidURL:
                print('\n',"--------------------------", '\n', "The client ID provided is not valid\n")
                return False
    
    def get_unconfigured_accounts(api_key, client_api_id = 0):
        base_url = 'chapi.cloudhealthtech.com'
        query = '/api/search.json?api_version=2&name=AwsAccount&query=status=\'Not-Configured\'&fields=owner_id,name'
        if client_api_id:
            query = query + '&client_api_id=%s' % client_api_id
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % api_key} 
        connection = http.client.HTTPSConnection(base_url)
        connection.request('GET', query, headers = headers)
        response =  json.loads(connection.getresponse().read().decode())
        connection.close()
        return response
    
    if customer_check(client_api_id, api_key) == False:
        is_customer = False
        unconfigured_accounts = get_unconfigured_accounts(api_key)
    else:
        is_customer = True
        unconfigured_accounts = get_unconfigured_accounts(api_key, client_api_id)
    
    def update_account(api_key, ch_account_id, friendly_name, role_arn, external_id, client_api_id = 0):
        base_url = 'chapi.cloudhealthtech.com'
        query = '/v1/aws_accounts/%s' % ch_account_id
        if client_api_id:
            query = query + '?client_api_id=%s' % client_api_id
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
    
    print('\n',"--------------------------", '\n')
    
    for item in unconfigured_accounts:
        role_arn = 'arn:aws:iam::%s:role/%s' % (item['owner_id'], arn_role_name)
        friendly_name = item['name']
        print('Owner ID: ', item['owner_id'], ', CH Account ID: ', item['id'], ', Friendly Name: ', friendly_name)
        if is_customer == True:
            update_account(api_key, item['id'], friendly_name, role_arn, external_id, client_api_id)
        else:
            update_account(api_key, item['id'], friendly_name, role_arn, external_id)
    print('\n',"--------------------------", '\n')
    return event
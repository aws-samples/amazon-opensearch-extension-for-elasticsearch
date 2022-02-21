from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import requests
import json
import boto3
import os

def handler(event, context):
    service = 'es'
    host = 'my-test-domain.us-east-1.es.amazonaws.com'
    region = 'us-east-1'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    es = Elasticsearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

    get_left_ultrawarm_indices_url = 'https://' + host + '/_warm'
    headers = {"Content-Type": "application/json"}

    uw_indices = requests.get(get_left_ultrawarm_indices_url, auth=awsauth, headers=headers)
    uw_indices = json.loads(uw_indices.text)

    for uw_index in uw_indices:
        print("Initiate migration for ", uw_index, " index from UltraWarm to Cold tier")
        move_to_cold_url = 'https://' + host + '/_ultrawarm/migration/' + uw_index + '/_cold?ignore=timestamp'
        move_to_cold = requests.post(move_to_cold_url, auth=awsauth, headers=headers)

    return {
        'statusCode': 200,
        'body': json.dumps('SUCCESS')
    }

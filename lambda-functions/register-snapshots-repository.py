from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import requests
import json
import boto3

def handler(event, context):
    service = 'es'
    host = 'my-test-domain.us-east-1.es.amazonaws.com'
    region = 'us-east-1'
    bucket = 'snapshots-bucket'
    role_arn = 'arn:aws:iam::123456789012:role/SnapshotsRole'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    es = Elasticsearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

    body = {
      "type": "s3",
      "settings": {
        "bucket": bucket,
        "region": region,
        "role_arn": role_arn,
        "readonly": "true"
      }
    }
    print(es.snapshot.create_repository(repository=bucket, body=body))

    return {
        'statusCode': 200,
        'body': json.dumps('SUCCESS')
    }

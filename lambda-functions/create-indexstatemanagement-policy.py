from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import requests
import json
import boto3

def handler(event, context):
    service = 'es'
    host = 'my-test-domain.us-east-1.es.amazonaws.com'
    region = 'us-east-1'
    policy_id = 'hot-ultrawarm-cold-delete'
    retention_periods = [14, 21, 35, 60, 90, 180]
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    es = Elasticsearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

    for period in retention_periods:
      print("Creates ISM policy for a retention period of", period, "days in Cold tier before being deleted.")
      payload = {
          "policy": {
          "description": "Hot-UltraWarm-Cold-Delete workflow.",
          "default_state": "hot",
          "schema_version": 1,
          "states": [{
              "name": "hot",
              "actions": [],
              "transitions": [{
                "state_name": "warm",
                "conditions": {
                  "min_index_age": "1m"
                }
              }]
            },
            {
              "name": "warm",
              "actions": [{
                "retry": {
                  "count": 5,
                  "delay": "1h"
                },
                "warm_migration": {}
              },
              {
                "replica_count": {
                  "number_of_replicas": 0
                }
              }],
              "transitions": [{
                "state_name": "cold",
                "conditions": {
                  "min_index_age": "1m"
                }
              }]
            },
            {
              "name": "cold",
              "actions": [{
                  "cold_migration": {
                    "timestamp_field": "timestamp"
                  }
                }
              ],
              "transitions": [{
                "state_name": "delete",
                "conditions": {
                  "min_index_age": str(period) + "d"
                }
              }]
            },
            {
              "name": "delete",
              "actions": [{
                "cold_delete": {}
              }]
            }
          ]
        }
      }
      put_ism_policy_url = 'https://' + host + '/_opendistro/_ism/policies/'
      url = put_ism_policy_url + policy_id + str(period)
      headers = {"Content-Type": "application/json"}

      r = requests.put(url, auth=awsauth, json=payload, headers=headers)

      print(r.status_code)
      print(r.text)

    return {
        'statusCode': 200,
        'body': json.dumps('SUCCESS')
    }

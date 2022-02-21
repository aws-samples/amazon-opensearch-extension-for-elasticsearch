from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import requests
import json
import boto3
import datetime
from datetime import date

def handler(event, context):
    service = 'es'
    host = 'my-test-domain.us-east-1.es.amazonaws.com'
    region = 'eu-west-3'
    bucket = 'snapshots-bucket'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    fourteen_days = 'aaa,bbb'
    twenty_one_days = 'ccc,ddd'
    thirty_five_days = 'eee,fff'
    sixty_days = 'ggg,hhh'
    ninety_days = 'iii,jjj'
    one_hundred_eighty_days = 'kkk,lll'

    es = Elasticsearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

    today_date = datetime.datetime.strptime(str(date.today()), '%Y-%m-%d').strftime('%Y-%m-%d')
    today_date = datetime.datetime.strptime(today_date, "%Y-%m-%d")
    today_date = today_date.date()

    print("TODAY'S DATE: ", today_date)
    print("\n\n")

    last_8days = []
    last_8days.append(str((today_date - datetime.timedelta(8))))
    last_8days.append(str((today_date - datetime.timedelta(7))))
    last_8days.append(str((today_date - datetime.timedelta(6))))
    last_8days.append(str((today_date - datetime.timedelta(5))))
    last_8days.append(str((today_date - datetime.timedelta(4))))
    last_8days.append(str((today_date - datetime.timedelta(3))))
    last_8days.append(str((today_date - datetime.timedelta(2))))
    last_8days.append(str((today_date - datetime.timedelta(1))))

    snapshots = es.snapshot.get(repository = bucket, snapshot = '_all')

    for snapshot in snapshots['snapshots']:
        print("\nSNAPSHOT ID:", snapshot['snapshot'])
        if snapshot['state'] != 'SUCCESS':
            print(snapshot['snapshot'], "has not been snapshotted with success. It is in", snapshot['state'], "status. Restore operation won't be initiated.")
        else:
            print(snapshot['snapshot'], "has been snapshotted with success.")
            for index in snapshot['indices']:
                if index[-10:] in last_8days:
                    #Index is within 8 last days
                    policy_id = os.environ['policy_id'] # e.g. hot-ultrawarm-cold-delete
                    index_settings = {
                        "indices": index,
                        "index_settings": {
                            "index.routing.allocation.require.box_type": "hot",
                            "index.routing.allocation.require.type": None,
                            "index.number_of_replicas": 0
                        }
                    }
                    #Check if not exist in Hot and UltraWarm tiers
                    exist = es.indices.exists(index)
                    if not(exist):
                        check_exists_cold_url = 'https://' + host + '/_cold/indices/_search'
                        payload = {
                            "filters":{
                              "index_pattern": index
                          }
                        }
                        headers = {"Content-Type": "application/json"}
                        cold_exists = requests.get(check_exists_cold_url, auth=awsauth, json=payload, headers=headers)
                        cold_exists = json.loads(cold_exists.text)

                        if cold_exists['total_results'] > 0: # Index exists within Cold tier
                            print(index, "exists already within the cluster (in Cold tier).")
                        else: # Index doesn't exist within Cold tier
                            # Index restore
                            es.snapshot.restore(bucket, snapshot['snapshot'], body=index_settings)
                            print(index, "imported.")
                            # Attach ISM policy to index
                            attach_ism_policy_url = 'https://' + host + '/_opendistro/_ism/add/'
                            url = attach_ism_policy_url + index
                            trigramme = index[5:8]
                            print("Trigramme:", trigramme)
                            if trigramme in fourteen_days:
                              print(trigramme, "has a retention policy of 14 days.")
                              policy_id = policy_id + "14"
                            elif trigramme in twenty_one_days:
                              print(trigramme, "has a retention policy of 21 days.")
                              policy_id = policy_id + "21"
                            elif trigramme in thirty_five_days:
                              print(trigramme, "has a retention policy of 35 days.")
                              policy_id = policy_id + "35"
                            elif trigramme in sixty_days:
                              print(trigramme, "has a retention policy of 60 days.")
                              policy_id = policy_id + "60"
                            elif trigramme in ninety_days:
                              print(trigramme, "has a retention policy of 90 days.")
                              policy_id = policy_id + "90"
                            elif trigramme in one_hundred_eighty_days:
                              print(trigramme, "has a retention policy of 90 days.")
                              policy_id = policy_id + "180"
                            else:
                              print(trigramme, "isn't recognized in any retention policy already existing.")
                            payload = {
                                "policy_id": policy_id
                            }
                            headers = {"Content-Type": "application/json"}
                            r = requests.post(url, auth=awsauth, json=payload, headers=headers)
                            print(policy_id, 'ISM policy attached to', index)
                            print(r.status_code)
                            print(r.text)
                    else:
                        print(index, "exists already within the cluster (either in Hot or in UltraWarm tier.)")
                else:
                    print(index, "is not from 8 last days. Not restored then.")

    return {
        'statusCode': 200,
        'body': json.dumps('SUCCESS')
    }

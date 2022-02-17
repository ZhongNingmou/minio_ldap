# imports required for get_credentials
import json
import os
import subprocess
import requests
from xml.etree import ElementTree as etree

MINIO_SERVER = os.environ.get("miniohost", 'localhost:9000')

def get_credentials_with_ldap(endpoint, username, password, duration=3600):
    """
    Get temporary access credentials to MinIO using LDAP user credentials
    through the MinIO Security Token Service (STS) API.

    Args:
        endpoint (str): Hostname of the MinIO API server.
        username (str): Username of the LDAP user as whom you want to authenticate.
        password (str): Password of the LDAP user specified in `username`.
        duration (int, optional): The duration for which the requested credentials
            will be valid for in seconds. Minimum value is 900. Defaults to 3600 (1 hour).

    Returns:
        dict: The details of the temporary credentials generated by MinIO. Contains
            `AccessKeyId`, `SecretAccessKey`, `Expiration`, and `SessionToken` keys.

    Raises:
        Exception: Raised when credentials cannot be successfully obtained from the MinIO STS API.
    """
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation"
                ],
                "Resource": [
                    "arn:aws:s3:::*"
                ]
            }
        ]
    }

    params = {
        "Action": "AssumeRoleWithLDAPIdentity",
        "LDAPUsername": username,
        "LDAPPassword": password,
        "Version": "2011-06-15",
        "Policy": json.dumps(policy),
        "DurationSeconds": duration
    }
    r = requests.post(f"http://{endpoint}", params=params)

    if r.status_code == 200:
        credentials = {}
        content = r.content
        root = etree.fromstring(content)
        ns = {"ns": "https://sts.amazonaws.com/doc/2011-06-15/"}
        et = root.find("ns:AssumeRoleWithLDAPIdentityResult/ns:Credentials", ns)
        for el in et:
            _, _, tag = el.tag.rpartition("}")
            credentials[tag] = el.text
        return credentials
    else:
        raise Exception(f"Unable to get credentials from MinIO STS API. Received response with status_code='{r.status_code}' and content='{r.content.decode('UTF-8')}'")

if __name__ == "__main__":
    # imports required for __main__
    from minio import Minio
    import pandas as pd
    import pprint

    # server = "localhost:9000"
    username = "n1"
    password = "123456"

    credentials = get_credentials_with_ldap(MINIO_SERVER, username, password, 1800)
    print("--------------------------------")
    pprint.pprint(credentials)
    print("--------------------------------")

    client = Minio(
        MINIO_SERVER,
        secure=False,
        access_key=credentials['AccessKeyId'],
        secret_key=credentials['SecretAccessKey'],
        session_token=credentials['SessionToken']
    )

    buckets = client.list_buckets()
    for bucket in buckets:
        print(bucket.name, bucket.creation_date)

    # bucket_name = "ningmou-test"
    file = client.get_object(
        "ningmou-test",
        "ningmou_test0.csv"
    )

    df = pd.read_csv(file)
    print(df)

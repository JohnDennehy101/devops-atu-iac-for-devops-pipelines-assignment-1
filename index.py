import json
import pymysql
import os
import boto3
import socket
from botocore.exceptions import ClientError

def get_db_credentials(secret_name: str, region_name: str):
  client = boto3.client("secretsmanager", region_name=region_name)
  try:
    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])
    return secret
  except ClientError as e:
    print("Error receiving secret: {}".format(e))
    raise

def lambda_handler(event, context):
  secret_name = os.environ["DB_SECRET_NAME"]
  region_name = os.environ["AWS_REGION"]

  try:
    credentials = get_db_credentials(secret_name, region_name)
  except Exception as e:
    return {
      "statusCode": 500,
      "body": json.dumps({"error": "Secrets Manager Access failed: {}".format(str(e))})
    }
  try:
    db_connection = pymysql.connect(
        host=os.environ["DB_HOST"], 
        user=credentials["username"],
        password=credentials["password"],
        database=credentials["dbname"])
  except Exception as e:
    return {
      "statusCode": 500,
      "body": json.dumps({"error": "DB Connection failed: {}".format(str(e))})
    }
  
  try:

    with db_connection.cursor() as cursor:
      cursor.execute("CREATE TABLE IF NOT EXISTS birthdays (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), birthday VARCHAR(10), idea VARCHAR(200), link VARCHAR(200));")
      cursor.execute("SELECT * FROM birthdays;")
      results = cursor.fetchall()
  
      if not results:
        cursor.execute("INSERT INTO birthdays (name, birthday, idea, link) VALUES ('John', '10-16', 'Cookbook', '');")
        db_connection.commit()
        cursor.execute("SELECT * FROM birthdays;")
        results = cursor.fetchall()
      

    return {
      "statusCode": 200,
      "headers": {"Content-Type": "application/json"},
      "body": json.dumps(results)
      }
  except Exception as e:
    return {
      "statusCode": 500,
      "body": json.dumps({"error": "DB Query failed: {}".format(str(e))})
    }

  finally:
    db_connection.close()
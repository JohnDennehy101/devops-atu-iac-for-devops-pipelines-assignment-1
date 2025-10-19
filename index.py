import json
import pymysql
from pymysql.cursors import DictCursor
import os
import boto3
import socket
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.logging import correlation_paths

connection = None
logger = Logger(service="BirthdayPresentTracker")
tracer = Tracer(service="BirthdayPresentTracker")
metrics = Metrics(namespace="BirthdayPresentTracker", service="API")

@tracer.capture_method
def get_db_credentials(secret_name: str, region_name: str):
  client = boto3.client("secretsmanager", region_name=region_name)
  try:
    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])
    logger.info("Successfully retrieved secret", extra={"secret_name": secret_name})
    return secret
  except ClientError as e:
    logger.exception("Error receiving secret: {}".format(e))
    metrics.add_metric(name="SecretsManagerAccessFailure", unit=MetricUnit.Count, value=1)
    raise

@tracer.capture_method
def get_db_connection(credentials):
  global connection
  try:
    if connection is None or not connection.open:
      connection = pymysql.connect(
          host=os.environ["DB_HOST"], 
          user=credentials["username"],
          password=credentials["password"],
          database=credentials["dbname"])
      logger.info("Successfully connected to DB", extra={"db_host": os.environ["DB_HOST"]})
    return connection
  except Exception as e:
    logger.exception("DB Connection failed: {}".format(str(e)))
    metrics.add_metric(name="DBConnectionFailure", unit=MetricUnit.Count, value=1)
    raise

@tracer.capture_method
def get_db_records(db_connection):
  try:
    with db_connection.cursor(DictCursor) as cursor:
      cursor.execute("CREATE TABLE IF NOT EXISTS birthdays (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), birthday VARCHAR(10), idea VARCHAR(200), link VARCHAR(200));")
      cursor.execute("SELECT * FROM birthdays;")
      results = cursor.fetchall()
  
      if not results:
        cursor.execute("INSERT INTO birthdays (name, birthday, idea, link) VALUES ('John', '10-16', 'Cookbook', '');")
        db_connection.commit()
        cursor.execute("SELECT * FROM birthdays;")
        results = cursor.fetchall()
      
    logger.info("DB query executed successfully", extra={"rows_returned": len(results)})
    metrics.add_metric(name="DBQuerySuccess", unit=MetricUnit.Count, value=1)
    return results
  except Exception as e:
    logger.exception("DB Query failed: {}".format(str(e)))
    metrics.add_metric(name="DBQueryFailure", unit=MetricUnit.Count, value=1)
    raise


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event, context):
  global connection
  secret_name = os.environ["DB_SECRET_NAME"]
  region_name = os.environ["AWS_REGION"]

  try:
    credentials = get_db_credentials(secret_name, region_name)
    db_connection = get_db_connection(credentials)
    results = get_db_records(db_connection)

    return {
      "statusCode": 200,
      "headers": {"Content-Type": "application/json"},
      "body": json.dumps(results)
    }
  except Exception as e:
    return {
      "statusCode": 500,
      "body": json.dumps({"error": "Internal server error"})
    }
    
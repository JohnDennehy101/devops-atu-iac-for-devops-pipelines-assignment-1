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
from datetime import datetime, date

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

def seed_db(conn):
  with conn.cursor() as cursor:
    cursor.execute("""
      CREATE TABLE IF NOT EXISTS birthdays(
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        birthday DATE NOT NULL,
        idea VARCHAR(200),
        link VARCHAR(400),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    """)
    cursor.execute("SELECT COUNT(*) AS count from birthdays;")
    if cursor.fetchone()[0] == 0:
      cursor.execute("INSERT INTO birthdays (name, birthday, idea) VALUES ('John Dennehy', '1994-05-12', 'AWS Course');")
    
    conn.commit()

def convert_date_for_output(date_object):
  if isinstance(date_object, (date, datetime)):
    return date_object.isoformat()
  raise TypeError("Type {} not serializable".format(type(date_object)))

def validate_date(date_str):
  try:
    return datetime.strptime(date_str, "%Y-%m-%d").date()
  except ValueError:
    return None

def validate_payload(data):
  errors = []
  birthday_date = None

  name = data.get("name", "").strip()
  idea = data.get("idea", "").strip()
  link = data.get("link", "").strip()

  if not name:
    errors.append("Missing name")
  elif len(name) > 200:
    errors.append("Name too long")
  
  if "birthday" not in data or not data["birthday"]:
    errors.append("Missing birthday")
  else:
    birthday_date = validate_date(data["birthday"])
    if not birthday_date:
      errors.append("Invalid birthday, expected YYYY-MM-DD")

  if not idea:
    errors.append("Missing 'idea'")
  elif len(idea) > 200:
    errors.append("Idea too long")
  
  if len(link) > 400:
    errors.append("link too long")
  
  return errors, birthday_date

@tracer.capture_method
def get_handler(db_connection):
  try:
    with db_connection.cursor(DictCursor) as cursor:
      cursor.execute("SELECT * FROM birthdays;")
      results = cursor.fetchall()
      
    logger.info("DB query executed successfully", extra={"rows_returned": len(results)})
    metrics.add_metric(name="DBQuerySuccess", unit=MetricUnit.Count, value=1)
    return {
      "statusCode": 200,
      "headers": {"Content-Type": "application/json"},
      "body": json.dumps(results, default=convert_date_for_output)
      }
  except Exception as e:
    logger.exception("DB Query failed: {}".format(str(e)))
    metrics.add_metric(name="DBQueryFailure", unit=MetricUnit.Count, value=1)
    raise

@tracer.capture_method()
def post_handler(db_connection, data):
  errors, birthday_date = validate_payload(data)
  if errors:
    return {"statusCode": 400, "body": json.dumps({"errors": errors})}
  
  with db_connection.cursor() as cursor:
    cursor.execute(
      "INSERT INTO birthdays (name, birthday, idea, link) VALUES (%s, %s, %s, %s);",
      (data["name"], birthday_date, data["idea"], data.get("link", ""))
    )
    db_connection.commit()
    new_id = cursor.lastrowid
  
  return {
    "statusCode": 201,
    "body": json.dumps({"message": "Record created successfully", "id": new_id})
  }

@tracer.capture_method()
def put_handler(db_connection, data):
  if "id" not in data:
    return {
      "statusCode": 400, 
      "body": json.dumps({"error": "Missing 'id' for update"})
      }

  errors, birthday_date = validate_payload(data)

  if errors:
    return {
      "statusCode": 400, 
      "body": json.dumps({"errors": errors})
      }
  

  with db_connection.cursor() as cursor:
    cursor.execute(
      "UPDATE birthdays SET name=%s, birthday=%s, idea=%s, link=%s WHERE id=%s;",
      (data["name"], birthday_date, data["idea"], data.get("link", ""), data["id"])
    )
    db_connection.commit()
    if cursor.rowcount == 0:
      return {
        "statusCode": 404, 
        "body": json.dumps({"error": "Record not found"})
        }
    
  return {
    "statusCode": 200,
    "body": json.dumps({"message": "Record updated"})
    }

@tracer.capture_method()
def delete_handler(db_connection, data):
  if "id" not in data:
    return {
      "statusCode": 400, 
      "body": json.dumps({"error": "Missing 'id' for delete"})
      }
  
  with db_connection.cursor() as cursor:
    cursor.execute(
      "DELETE FROM birthdays WHERE id=%s;",
      (data["id"],)
    )
    db_connection.commit()

    if cursor.rowcount == 0:
      return {
        "statusCode": 404, 
        "body": json.dumps({"error": "Record not found"})
        }
  
  return {
    "statusCode": 200,
    "body": json.dumps({"message": "Record deleted"})
    }

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
    seed_db(db_connection)

    method = event["httpMethod"]
    if method == "GET":
      return get_handler(db_connection)
    
    try:
      raw_data = event.get("body", "{}")
      data = json.loads(raw_data)
    except json.JSONDecodeError:
      return {
        "statusCode": 400,
        "body": json.dumps({"error": "invalid JSON payload"})
      }
    
    if method == "POST":
      return post_handler(db_connection, data)
    elif method == "PUT":
      return put_handler(db_connection, data)
    elif method == "DELETE":
      return delete_handler(db_connection, data)
    else:
      return {
        "statusCode": 405,
        "body": json.dumps({"error": "Method not allowed"})
      }

  except Exception as e:
    logger.exception("Unhandled exception")
    return {
      "statusCode": 500,
      "body": json.dumps({"error": "Internal server error"})
    }
    
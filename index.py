import json
import pymysql
import os

def lambda_handler(event, context):
  db_connection = pymysql.connect(
  host=os.environ["DB_HOST"], 
  user=os.environ["DB_USER"],
  password=os.environ["DB_PASSWORD"],
  database=os.environ["DB_NAME"])

  with db_connection.cursor() as cursor:
    cursor.execute("CREATE TABLE IF NOT EXISTS birthdays (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100), birthday VARCHAR(10), idea VARCHAR(200), link VARCHAR(200));")
    cursor.execute("SELECT * FROM birthdays;")
    results = cursor.fetchall()
  
  if not results:
    with db_connection.cursor() as cursor:
      cursor.execute("INSERT INTO birthdays (name, birthday, idea, link) VALUES ('John', '10-16', 'Cookbook', '');")
      db_connection.commit()
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM birthdays;")
    results = cursor.fetchall()
  
  db_connection.close()

  return {
    "statusCode": 200,
    "headers": {"Content-Type": "application/json"},
    "body": json.dumps(results)
  }
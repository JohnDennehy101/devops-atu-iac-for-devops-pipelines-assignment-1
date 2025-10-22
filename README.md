# devops-atu-iac-for-devops-pipelines-assignment-1

## Creating lambda on S3 with external pymysql package installed (manual process - will automate in future PR with Github actions pipeline)

Create lambda code with external pymysql package installed

```
mkdir package
pip install pymysql -t package/
cp index.py package/
cd package
zip -r ../birthday_present_tracker_lambda.zip .
```

Upload to s3 manually (manual creation of bucket and then upload of zipped directory from above)

```
cd ..
aws s3 mb s3://birthday-present-tracker-lambda-deployment-bucket
aws s3 cp birthday_present_tracker_lambda.zip s3://birthday-present-tracker-lambda-deployment-bucket/birthday_present_lambda.zip
```

## Methods

### GET

Returns a list of all records

```
$APIEndpoint/birthdays
```

Sample success response

Response code: 200

```
[{"id": 1, "name": "John Dennehy", "birthday": "1994-05-10", "idea": "AWS Course", "link": null, "created_at": "2025-10-21T10:10:51"}]
```

### POST

Adds a new record

```
$APIEndpoint/birthdays
```

Sample Payload

```
{
  "name": "Alice Smith",
  "birthday": "1990-07-15",
  "idea": "Book",
  "link": "https://example.com/book"
}
```

Sample Success Response

Response code: 201

```
{
  "message": "Record created successfully",
  "id": 2
}
```

Sample error response, empty payload

Response code: 400

```
{
  "error": "invalid JSON payload"
}
```

Sample error response, invalid payload

Response code: 400

```
{
  "errors": ["Missing name"]
}
```

### PUT

Updates an existing record

```
$APIEndpoint/birthdays
```

Sample payload

```
{
  "id": 1,
  "name": "John D",
  "birthday": "1994-07-25",
  "idea": "AWS Course Updated",
  "link": "https://example.com/aws-course"
}
```

Sample success Response

Response code: 200

```
{
  "message": "Record updated"
}
```

Sample error response, empty payload

Response code: 400

```
{
  "error": "invalid JSON payload"
}
```

Sample error response, invalid payload

Response code: 400

```
{
  "errors": ["Missing name"]
}
```

Sample error response, record not found

Response code: 404

```
{
  "error": {"Record not found"}
}
```

### DELETE

Deletes an existing record

```
$APIEndpoint/birthdays
```

Sample payload

```
{
  "id": 1
}
```

Sample success response

Response code: 200

```
{
  "message": "Record deleted"
}
```

Sample error response, empty payload

Response code: 400

```
{
  "error": "invalid JSON payload"
}
```

Sample error response, invalid payload

Response code: 400

```
{
  "error": {"Missing 'id' for delete"}
}
```

Sample error response, record not found

Response code: 404

```
{
  "error": {"Record not found"}
}
```

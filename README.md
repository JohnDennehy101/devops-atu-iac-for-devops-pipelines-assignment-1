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
aws s3 mb s3://birthday-present-tracker-lambda-deployment-bucket
aws s3 cp birthday_present_tracker_lambda.zip s3://birthday-present-tracker-lambda-deployment-bucket/birthday_present_lambda.zip
```

# AWS Lambda function for updating Route53 record with EC2 public IP address

In the case of AWS EC2, it's public IP address (not Elastic IP) changes fluidly.

This function performs the function of inserting/updating the host record of Route53 (DNS) automatically using the CloudWatch event of EC2 state changing, considering that the public IP change when EC2 is started.

This function is available at **[AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:884430845962:applications~Update-Route53-Record-to-Ec2-PublicIp-Python3)** too.

## Features
- Serverless, Works only on the AWS layer without any OS manipulation.
- Supports multiple EC2 + Route53 Record pairs with a single Lambda function.
- A new EC2 + Route53 Record pair can attach simply by adding EC2 tag only without modifying the source or AWS configuration.
- Supports CNAME or A record type and Record TTL can be specified.

## How to use this?

1. Please deploy the application and specify threshold.
2. Add FQDN as **Route53FQDN** tag to each EC2 instances that you want to register record of public IP to Route53.
3. Now your Route53 records will update when state of EC instances changed to **running**.

## Lambda environment variables

- **dns_tag_key** : (Optional) EC2 Tag key for define FQDN.
    - Default value : Route53FQDN
- **dns_record_type** : (Optional) Route53 record type. (CNAME or A)
    - Default value : CNAME
- **dns_record_ttl** : (Optional) TTL value of Route53 record
    - Default value : 60

## Execution IAM policy
This Serverless application creates a IAM policy as below.
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeTags",
        "route53:ListHostedZones",
        "route53:ChangeResourceRecordSets"
      ],
      "Resource": "*"
    }
  ]
}
```

## FAQ

- Do I need to create a Route53 zone or record in advance?
    - If there is no zone containing the provided FQDN, an error occurs. **The zone must be created in advance**.
    - However, if the zone exists, but no record, this function generates new record.
    - If both zone and record are present, this function updates the record.
- What about EC2 without the tag?
    - The state change of EC2 which is not tagged is recorded only in the log without any action.
- Monitoring all EC instances is inefficient!
    - After deployment, a CloudWatch-Rule is generated to monitor EC2 states. The default rule will monitor all EC2 state changes.
    - If you put an **instance-id** entry in the CloudWatch-Rule as in the example below, the CloudWatch will only monitor those instances.
        ```json
        {
          "source": [
            "aws.ec2"
          ],
          "detail-type": [
            "EC2 Instance State-change Notification"
          ],
          "detail": {
            "state": [
              "running"
            ],
            "instance-id": [
              "i-01234567890123456",
              "i-12345678901234567"
            ]
          }
        }
        ```
- Changing Route53 record type between **CNAME** and **A**
    - You can change Route53 record type, if you define a **dns_record_type** Lambda function environment variable.
    - However, when changing the record type, please **delete the previous record in Route53 zone manually first**. At the AWS API, record updating is not supported between different record types. I don't want to include a delete processing in this function.
- My Route53 has a secondary-level domain(2LD) zone and its child third-level domain(3LD) zone concurrently. Which zone's record will change?
    - If there are multiple parent domain zones within your AWS account, **this function will change records in the lowest child domain zone** that matches the FQDN provided.


## License

MIT License (MIT)

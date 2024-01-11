import os

import pulumi
import pulumi_aws as aws
import json

class StorageComponent(pulumi.ComponentResource):
    def __init__(self, name, *args, **kwargs):
        self.env_name = os.environ.get('ENVIRONMENT_NAME', 'stage')

        project = pulumi.get_project()
        stack = pulumi.get_stack()
        bucket_name = f"strongmind-{project}-{stack}"
        tags = {
            "product": project,
            "repository": project,
            "service": project,
            "environment": self.env_name
        }
        self.bucket = aws.s3.BucketV2("bucket",
                                      bucket=bucket_name,
                                      tags=tags
                                      )

        self.bucket_ownership_controls = aws.s3.BucketOwnershipControls("bucket_ownership_controls",
                                                                        bucket=self.bucket.id,
                                                                        rule=aws.s3.BucketOwnershipControlsRuleArgs(
                                                                            object_ownership="BucketOwnerPreferred",
                                                                        ))
        self.bucket_public_access_block = aws.s3.BucketPublicAccessBlock("bucket_public_access_block",
                                                                         bucket=self.bucket.id,
                                                                         block_public_acls=kwargs.get('storage_private', True),
                                                                         block_public_policy=kwargs.get('storage_private', True),
                                                                         ignore_public_acls=kwargs.get('storage_private', True),
                                                                         restrict_public_buckets=kwargs.get('storage_private', True)
                                                                         )

        acl_opts = pulumi.ResourceOptions(
            depends_on=[self.bucket_ownership_controls, self.bucket_public_access_block])  # pragma: no cover
        if kwargs.get('storage_private') == False:
            acl = "public-read"
        else:
            acl = "private"
        self.bucket_acl = aws.s3.BucketAclV2("bucket_acl",
                                             bucket=self.bucket.id,
                                             acl=acl,
                                             opts=acl_opts
                                             )
        self.s3_user = aws.iam.User("s3User", name=f"{project}-{stack}-s3User-", tags=tags)
        self.s3_policy = aws.iam.Policy("s3Policy",
            name=f"{project}-{stack}-s3Policy",
            policy=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject"
                    ],
                    "Resource": [f"arn:aws:s3:::{self.bucket.bucket}/*"]
                }]
            }),
            tags=tags
            )
        aws.iam.UserPolicyAttachment("railsAppUserPolicyAttachment",
            user=self.s3_user.name,
            policy_arn=self.s3_policy.arn)
        self.s3_user_secret_access_key = aws.iam.AccessKey("railsAppUserAccessKey", user=self.s3_user.name)
        self.s3_user_access_key_id = self.s3_user_secret_access_key.id
        self.s3_env_vars = {
            "S3_BUCKET_NAME": self.bucket.bucket,
            "AWS_ACCESS_KEY_ID": self.s3_user_access_key_id,
            "AWS_SECRET_ACCESS_KEY": self.s3_user_secret_access_key.secret
        }

import pulumi
import pulumi_aws as aws
from pulumi import Output
import os
import json

class SecretsComponent(pulumi.ComponentResource):
    def __init__(self, name, opts=None, **kwargs):
        """
        Resource that creates a SecretsManager secret.

        :param name: The _unique_ name of the resource.
        :param opts: Not used in this resource, but provided for consistency with Pulumi components.
        """
        super().__init__('strongmind:global_build:commons:secretsmanager', name, None, opts)

        self.env_name = os.environ.get('ENVIRONMENT_NAME', 'stage')
        self.formatted_secrets = []

        project = pulumi.get_project()
        stack = pulumi.get_stack()
        project_stack = f"{project}-{stack}-devops-9495"

        self.tags = {
            "product": project,
            "repository": project,
            "service": project,
            "environment": self.env_name,
        }

        self.sm_secret = aws.secretsmanager.Secret(
            f"{project_stack}-secrets",
            name=f"{project_stack}-secrets",
            tags=self.tags
        )

        # put initial dummy secret value
        self.sm_secret_version = aws.secretsmanager.SecretVersion(
            f"{project_stack}-secrets-version",
            secret_id=self.sm_secret.arn,
            secret_string=json.dumps({})
        )
        self.register_outputs({})
    
    def get_secrets(self, sm_secret_arn):
        formatted_secrets = []

        secret_value = aws.secretsmanager.get_secret_version(
            secret_id=sm_secret_arn,
        )
        secrets = json.loads(secret_value.secret_string)
        for secret in secrets.keys():
            formatted_secrets.append(
                {
                    "name": secret,
                    "valueFrom": f"{secret_value.arn}:{secret}",
                }
            )

        return formatted_secrets

import json
import os

import pulumi.runtime
import pytest
from pytest_describe import behaves_like

from tests.mocks import get_pulumi_mocks
from tests.shared import assert_output_equals, assert_outputs_equal


def a_pulumi_containerized_app():
    @pytest.fixture
    def app_name(faker):
        return faker.word()

    @pytest.fixture
    def environment(faker):
        os.environ["ENVIRONMENT_NAME"] = faker.word()
        return os.environ["ENVIRONMENT_NAME"]

    @pytest.fixture
    def stack(environment):
        return environment

    @pytest.fixture
    def pulumi_mocks(faker):
        return get_pulumi_mocks(faker)

    @pytest.fixture
    def app_path(faker):
        return f'./{faker.word()}'

    @pytest.fixture
    def container_port(faker):
        return faker.random_int()

    @pytest.fixture
    def cpu(faker):
        return faker.random_int()

    @pytest.fixture
    def memory(faker):
        return faker.random_int()

    @pytest.fixture
    def entry_point(faker):
        return f'./{faker.word()}'

    @pytest.fixture
    def command(faker):
        return f'./{faker.word()}'

    @pytest.fixture
    def aws_account_id(faker):
        return faker.random_int()

    @pytest.fixture
    def container_image(aws_account_id, app_name):
        return f"{aws_account_id}.dkr.ecr.us-west-2.amazonaws.com/{app_name}:latest"

    @pytest.fixture
    def env_vars(faker, environment):
        return {
            "ENVIRONMENT_NAME": environment,
        }

    @pytest.fixture
    def secrets(faker):
        return [{
            faker.word(): faker.password(),
        }]

    @pytest.fixture
    def zone_id(faker):
        return faker.word()

    @pytest.fixture
    def load_balancer_dns_name(faker):
        return f"{faker.word()}.{faker.word()}.{faker.word()}"

    @pytest.fixture
    def resource_record_name(faker):
        return f"{faker.word()}.{faker.word()}.{faker.word()}"

    @pytest.fixture
    def resource_record_value(faker):
        return f"{faker.word()}.{faker.word()}.{faker.word()}"

    @pytest.fixture
    def resource_record_type(faker):
        return faker.word()

    @pytest.fixture
    def domain_validation_options(faker, resource_record_name, resource_record_value, resource_record_type):
        class FakeValidationOption:
            def __init__(self, name, value, type):
                self.resource_record_name = name
                self.resource_record_value = value
                self.resource_record_type = type

            pass

        return [FakeValidationOption(resource_record_name, resource_record_value, resource_record_type)]

    @pytest.fixture
    def need_load_balancer():
        return True

    @pytest.fixture
    def component_kwargs(pulumi_set_mocks,
                         app_name,
                         app_path,
                         container_port,
                         cpu,
                         memory,
                         entry_point,
                         command,
                         container_image,
                         env_vars,
                         secrets,
                         zone_id,
                         load_balancer_dns_name,
                         domain_validation_options,
                         ):
        return {
            "app_path": app_path,
            "container_port": container_port,
            "cpu": cpu,
            "memory": memory,
            "entry_point": entry_point,
            "command": command,
            "container_image": container_image,
            "env_vars": env_vars,
            "secrets": secrets,
            "zone_id": zone_id,
            "load_balancer_dns_name": load_balancer_dns_name,
            "domain_validation_options": domain_validation_options
        }

    @pytest.fixture
    def sut(component_kwargs):
        import strongmind_deployment.container
        return strongmind_deployment.container.ContainerComponent("container",
                                                                  **component_kwargs
                                                                  )

    def it_exists(sut):
        assert sut


@behaves_like(a_pulumi_containerized_app)
def describe_container():
    def describe_a_container_component():
        @pulumi.runtime.test
        def it_creates_an_ecs_cluster(sut):
            assert sut.ecs_cluster

        @pulumi.runtime.test
        def it_sets_the_cluster_name(sut, stack, app_name):
            def check_cluster_name(args):
                cluster_name = args[0]
                assert cluster_name == f"{app_name}-{stack}"

            return pulumi.Output.all(sut.ecs_cluster.name).apply(check_cluster_name)

        @pulumi.runtime.test
        def it_has_environment_variables(sut, app_name, env_vars):
            assert sut.env_vars == env_vars

        @pulumi.runtime.test
        def it_has_an_execution_role(sut):
            assert sut.execution_role

        @pulumi.runtime.test
        def it_has_a_task_role_named(sut, stack, app_name):
            return assert_output_equals(sut.task_role.name, f"{app_name}-{stack}-task-role")

        @pulumi.runtime.test
        def it_has_an_execution_role_named(sut, stack, app_name):
            return assert_output_equals(sut.execution_role.name, f"{app_name}-{stack}-execution-role")

        @pulumi.runtime.test
        def it_has_a_task_role_with_access_to_ecs(sut):
            return assert_output_equals(sut.task_role.assume_role_policy, json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "ecs-tasks.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }))

        @pulumi.runtime.test
        def it_has_a_task_policy_named(sut, stack, app_name):
            return assert_output_equals(sut.task_policy.name, f"{app_name}-{stack}-task-policy")

        @pulumi.runtime.test
        def it_has_task_policy_attached_to_task_role(sut):
            return assert_outputs_equal(sut.task_policy.role, sut.task_role.id)

        @pulumi.runtime.test
        def it_has_execution_policy_attached_to_execution_role(sut):
            return assert_outputs_equal(sut.execution_policy.role, sut.execution_role.id)

        @pulumi.runtime.test
        def it_has_an_execution_policy_named(sut, stack, app_name):
            return assert_output_equals(sut.execution_policy.name, f"{app_name}-{stack}-execution-policy")

        @pulumi.runtime.test
        def it_has_a_task_policy_with_ssmmessages_access(sut):
            return assert_output_equals(sut.task_policy.policy, json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream",
                                "ecs:UpdateTaskProtection",
                                "ssmmessages:CreateControlChannel",
                                "ssmmessages:CreateDataChannel",
                                "ssmmessages:OpenControlChannel",
                                "ssmmessages:OpenDataChannel",
                                "cloudwatch:*",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                                "s3:GetObject",
                                "s3:PutObject*",
                                "s3:DeleteObject",
                            ],
                            "Effect": "Allow",
                            "Resource": "*",
                        }
                    ],
                }))

        @pulumi.runtime.test
        def it_creates_an_s3_policy_with_storage_enabled(sut):
            @pytest.fixture
            def component_kwargs(component_kwargs):
                component_kwargs['storage'] = True

                return component_kwargs
            
            @pulumi.runtime.test
            def it_has_an_s3_policy_named(sut, stack, app_name):
                return assert_output_equals(sut.s3_policy.name, f"{app_name}-{stack}-s3-policy")
                     
            @pulumi.runtime.test
            def it_has_an_s3_policy_with_storage_access(sut):
                return assert_output_equals(sut.s3_policy.policy, json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject"
                        ],
                        "Resource": "*"
                    }]
                }),
                tags=tags
                )
            
            @pulumi.runtime.test
            def test_s3_policy_attachment():
                def check_s3_policy_attachment(args):
                    sut, expected_role, expected_policy_arn = args
                    assert_output_equals(sut.s3_policy_attachment.role, expected_role)
                    assert_output_equals(sut.s3_policy_attachment.policy_arn, expected_policy_arn)

                return pulumi.Output.all(sut, sut.task_role.id, sut.s3_policy.arn).apply(check_s3_policy_attachment)
            
        @pulumi.runtime.test
        def it_enables_enable_execute_command(sut):
            return assert_output_equals(sut.fargate_service.enable_execute_command, True)

        @pulumi.runtime.test
        def its_execution_role_has_an_arn(sut):
            return assert_output_equals(sut.execution_role.arn,
                                        "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy")

        @pulumi.runtime.test
        def it_has_no_autoscaling_target(sut):
            assert not sut.autoscaling_target

        def describe_with_no_load_balancer():
            @pytest.fixture
            def need_load_balancer():
                return False

            @pytest.fixture
            def sut(need_load_balancer):
                import strongmind_deployment.container
                return strongmind_deployment.container.ContainerComponent("container",
                                                                          need_load_balancer=need_load_balancer)

            @pulumi.runtime.test
            def test_it_does_not_create_a_load_balancer(sut, need_load_balancer):
                assert not sut.load_balancer

            @pulumi.runtime.test
            def it_has_no_grace_period(sut):
                return assert_output_equals(sut.fargate_service.health_check_grace_period_seconds, None)

        def describe_load_balancer():
            @pulumi.runtime.test
            def it_creates_a_load_balancer(sut):
                assert sut.load_balancer

            @pulumi.runtime.test
            def it_sets_the_load_balancer_name(sut, stack, app_name):
                assert sut.load_balancer._name == f"{app_name}-{stack}"

            @pulumi.runtime.test
            def it_sets_the_access_log_bucket(sut, stack, app_name):
                expected = {
                    "bucket": "loadbalancer-logs-221871915463",
                    "enabled": True,
                    "prefix": f"{app_name}-{stack}",
                }

                def compare(value):
                    try:
                        assert str(value) == str(expected)
                    except AssertionError:
                        print(f"Expected: {expected}")
                        print(f"Actual: {value}")
                        raise

                return sut.load_balancer.access_logs.apply(compare)

            def describe_target_group():
                @pulumi.runtime.test
                def it_sets_the_target_group_port(sut, container_port):
                    return assert_output_equals(sut.target_group.port, container_port)

                @pulumi.runtime.test
                def it_sets_the_target_group_target_type(sut):
                    return assert_output_equals(sut.target_group.target_type, "ip")

                @pulumi.runtime.test
                def it_sets_the_target_group_health_check_enabled(sut):
                    return assert_output_equals(sut.target_group.health_check.enabled, True)

                @pulumi.runtime.test
                def it_sets_the_target_group_health_check_healthy_threshold(sut):
                    return assert_output_equals(sut.target_group.health_check.healthy_threshold, 5)

                @pulumi.runtime.test
                def it_sets_the_target_group_health_check_unhealthy_threshold(sut):
                    return assert_output_equals(sut.target_group.health_check.unhealthy_threshold, 2)

                @pulumi.runtime.test
                def it_sets_the_target_group_health_check_interval(sut):
                    return assert_output_equals(sut.target_group.health_check.interval, 30)

                @pulumi.runtime.test
                def it_sets_the_target_group_health_check_matcher_to_200(sut):
                    return assert_output_equals(sut.target_group.health_check.matcher, "200")

                @pulumi.runtime.test
                def it_sets_the_target_group_health_check_path_to_up(sut):
                    return assert_output_equals(sut.target_group.health_check.path, "/up")

                @pulumi.runtime.test
                def it_sets_the_target_group_health_check_protocol(sut):
                    return assert_output_equals(sut.target_group.health_check.protocol, "HTTP")

                @pulumi.runtime.test
                def it_sets_the_target_group_health_check_timeout(sut):
                    return assert_output_equals(sut.target_group.health_check.timeout, 5)

            def describe_the_load_balancer_listener_for_https():
                @pytest.fixture
                def listener(sut):
                    return sut.load_balancer_listener

                @pytest.fixture
                def listener_rule(sut):
                    return sut.listener_rule

                @pulumi.runtime.test
                def it_has_load_balancer_listener_for_https(listener):
                    assert listener

                @pulumi.runtime.test
                def it_sets_the_load_balancer_arn(listener, sut):
                    return assert_outputs_equal(listener.load_balancer_arn, sut.load_balancer.arn)

                @pulumi.runtime.test
                def it_sets_the_certificate_arn(listener, sut):
                    return assert_outputs_equal(listener.certificate_arn, sut.cert.arn)

                @pulumi.runtime.test
                def it_sets_the_port(listener):
                    return assert_output_equals(listener.port, 443)

                @pulumi.runtime.test
                def it_sets_the_protocol(listener):
                    return assert_output_equals(listener.protocol, "HTTPS")

                @pulumi.runtime.test
                def it_has_a_listener_rule_connected_to_the_listener(listener_rule, listener):
                    return assert_outputs_equal(listener_rule.listener_arn, listener.arn)

                @pulumi.runtime.test
                def it_forwards_to_the_target_group_with_a_rule(listener_rule, sut):
                    return assert_outputs_equal(listener_rule.actions[0].target_group_arn, sut.target_group.arn)

                @pulumi.runtime.test
                def it_forwards(listener_rule):
                    return assert_output_equals(listener_rule.actions[0].type, "forward")

            def describe_the_load_balancer_listener_for_http():
                @pytest.fixture
                def listener(sut):
                    return sut.load_balancer_listener_redirect_http_to_https

                @pulumi.runtime.test
                def it_has_load_balancer_listener_for_http(listener):
                    assert listener

                @pulumi.runtime.test
                def it_sets_the_load_balancer_arn(listener, sut):
                    return assert_outputs_equal(listener.load_balancer_arn, sut.load_balancer.arn)

                @pulumi.runtime.test
                def it_sets_the_port(listener):
                    return assert_output_equals(listener.port, 80)

                @pulumi.runtime.test
                def it_sets_the_protocol(listener):
                    return assert_output_equals(listener.protocol, "HTTP")

                @pytest.fixture
                def redirect_action(listener):
                    return listener.default_actions[0]

                @pulumi.runtime.test
                def it_redirects_to_443(redirect_action):
                    return assert_output_equals(redirect_action.redirect.port, "443")

                @pulumi.runtime.test
                def it_redirects_to_https(redirect_action):
                    return assert_output_equals(redirect_action.redirect.protocol, "HTTPS")

                @pulumi.runtime.test
                def it_redirects_with_301(redirect_action):
                    return assert_output_equals(redirect_action.redirect.status_code, "HTTP_301")

                @pulumi.runtime.test
                def it_redirects(redirect_action):
                    return assert_output_equals(redirect_action.type, "redirect")

        @pulumi.runtime.test
        def describe_the_fargate_service():
            @pulumi.runtime.test
            def it_creates_a_fargate_service(sut):
                assert sut.fargate_service

            @pulumi.runtime.test
            def it_propagate_tags(sut):
                return assert_output_equals(sut.fargate_service.propagate_tags, "SERVICE")

            @pulumi.runtime.test
            def it_has_a_ten_minute_grace_period(sut):
                return assert_output_equals(sut.fargate_service.health_check_grace_period_seconds, 600)

            @pulumi.runtime.test
            def it_has_the_cluster(sut):
                # arn is None at design time so this test doesn't really work
                def check_cluster(args):
                    service_cluster, cluster = args
                    assert service_cluster == cluster

                return pulumi.Output.all(sut.fargate_service.cluster,
                                         sut.ecs_cluster.arn).apply(check_cluster)

            @pulumi.runtime.test
            def it_has_task_definition(sut, container_port, cpu, memory, entry_point, command, stack, app_name,
                                       secrets):
                def check_task_definition(args):
                    task_definition_dict = args[0]
                    container = task_definition_dict["container"]
                    assert container["cpu"] == cpu
                    assert container["memory"] == memory
                    assert container["essential"]
                    assert container["secrets"] == secrets
                    assert container["entryPoint"] == entry_point
                    assert container["command"] == command
                    assert container["portMappings"][0]["containerPort"] == container_port
                    assert container["portMappings"][0]["hostPort"] == container_port
                    assert container["logConfiguration"]["logDriver"] == "awslogs"
                    assert container["logConfiguration"]["options"]["awslogs-group"] == f"/aws/ecs/{app_name}-{stack}"
                    assert container["logConfiguration"]["options"]["awslogs-region"] == "us-west-2"
                    assert container["logConfiguration"]["options"]["awslogs-stream-prefix"] == "container"

                return pulumi.Output.all(sut.fargate_service.task_definition_args).apply(check_task_definition)

            @pulumi.runtime.test
            def it_sends_env_vars_to_the_task_definition(sut, env_vars):
                def check_env_vars(args):
                    task_definition_dict = args[0]
                    env_var_key_value_pair_array = []
                    for var in env_vars:
                        env_var_key_value_pair_array.append({
                            "name": var,
                            "value": env_vars[var]
                        })
                    assert task_definition_dict["container"]["environment"] == env_var_key_value_pair_array

                return pulumi.Output.all(sut.fargate_service.task_definition_args).apply(check_env_vars)

            @pulumi.runtime.test
            def it_sets_the_image(sut, container_image):
                def check_image_tag(args):
                    task_definition_container_image = args[0]
                    assert task_definition_container_image == container_image

                return pulumi.Output.all(sut.fargate_service.task_definition_args["container"]["image"]).apply(
                    check_image_tag)

            @pulumi.runtime.test
            def it_sets_the_execution_role(sut):
                return assert_outputs_equal(sut.fargate_service.task_definition_args["executionRole"]["roleArn"], sut.execution_role.arn)

            @pulumi.runtime.test
            def it_sets_the_task_role(sut):
                return assert_outputs_equal(sut.fargate_service.task_definition_args["taskRole"]["roleArn"], sut.task_role.arn)

        def describe_with_custom_health_check_path():
            @pytest.fixture
            def custom_health_check_path(faker):
                return f"/{faker.word()}"

            @pytest.fixture
            def component_kwargs(component_kwargs, custom_health_check_path):
                component_kwargs["custom_health_check_path"] = custom_health_check_path
                return component_kwargs

            @pulumi.runtime.test
            def it_sets_the_target_group_health_check_path(sut, custom_health_check_path):
                return assert_output_equals(sut.target_group.health_check.path, custom_health_check_path)

    def describe_dns():
        @pulumi.runtime.test
        def it_has_cname_record(sut):
            assert sut.cname_record

        @pulumi.runtime.test
        def it_has_name_with_environment_prefix(sut, stack, app_name):
            return assert_output_equals(sut.cname_record.name, f"{stack}-{app_name}")

        def describe_in_production():
            @pytest.fixture
            def environment():
                os.environ["ENVIRONMENT_NAME"] = "prod"
                return "prod"

            @pulumi.runtime.test
            def it_has_name_without_prefix(sut, app_name):
                return assert_output_equals(sut.cname_record.name, app_name)

        @pulumi.runtime.test
        def it_has_cname_type(sut):
            return assert_output_equals(sut.cname_record.type, "CNAME")

        @pulumi.runtime.test
        def it_has_zone(sut, zone_id):
            return assert_output_equals(sut.cname_record.zone_id, zone_id)

        @pulumi.runtime.test
        def it_points_to_load_balancer(sut, load_balancer_dns_name):
            return assert_output_equals(sut.cname_record.value, load_balancer_dns_name)

    def describe_cert():
        @pulumi.runtime.test
        def it_has_cert(sut):
            assert sut.cert

        @pulumi.runtime.test
        def it_has_fqdn(sut, app_name, environment):
            return assert_output_equals(sut.cert.domain_name, f"{environment}-{app_name}.strongmind.com")

        @pulumi.runtime.test
        def it_validates_with_dns(sut):
            return assert_output_equals(sut.cert.validation_method, "DNS")

        @pulumi.runtime.test
        def it_adds_validation_record(sut):
            assert sut.cert_validation_record

        @pulumi.runtime.test
        def it_adds_validation_record_with_name(sut, resource_record_name):
            return assert_output_equals(sut.cert_validation_record.name, resource_record_name)

        @pulumi.runtime.test
        def it_adds_validation_record_with_type(sut, resource_record_type):
            return assert_output_equals(sut.cert_validation_record.type, resource_record_type)

        @pulumi.runtime.test
        def it_adds_validation_record_with_zone_id(sut, zone_id):
            return assert_output_equals(sut.cert_validation_record.zone_id, zone_id)

        @pulumi.runtime.test
        def it_adds_validation_record_with_value(sut, resource_record_value):
            return assert_output_equals(sut.cert_validation_record.value, resource_record_value)

        @pulumi.runtime.test
        def it_adds_validation_record_with_ttl(sut):
            return assert_output_equals(sut.cert_validation_record.ttl, 1)

        @pulumi.runtime.test
        def it_adds_validation_cert(sut):
            assert sut.cert_validation_cert

        @pulumi.runtime.test
        def it_adds_validation_cert_with_cert_arn(sut):
            return assert_outputs_equal(sut.cert_validation_cert.certificate_arn, sut.cert.arn)

        @pulumi.runtime.test
        def it_adds_validation_cert_with_fqdns(sut):
            return assert_outputs_equal(sut.cert_validation_cert.validation_record_fqdns,
                                        [sut.cert_validation_record.hostname])

    def describe_with_existing_cluster():
        @pytest.fixture
        def existing_cluster_arn(faker):
            return faker.word()

        @pytest.fixture
        def sut(existing_cluster_arn):
            import strongmind_deployment.container
            return strongmind_deployment.container.ContainerComponent("container",
                                                                      need_load_balancer=False,
                                                                      ecs_cluster_arn=existing_cluster_arn)

        @pulumi.runtime.test
        def it_uses_existing_cluster(sut, existing_cluster_arn):
            return assert_output_equals(sut.fargate_service.cluster, existing_cluster_arn)

    def describe_logs():
        @pulumi.runtime.test
        def it_creates_a_log_group(sut, stack, app_name):
            return assert_output_equals(sut.logs.name, f"/aws/ecs/{app_name}-{stack}")

        @pulumi.runtime.test
        def it_sets_retention(sut):
            return assert_output_equals(sut.logs.retention_in_days, 14)

        @pulumi.runtime.test
        def it_has_no_filters(sut):
            return sut.log_metric_filters == []

        def describe_with_job_filters():
            @pytest.fixture
            def waiting_workers_pattern():
                return "[LETTER, DATE, LEVEL, SEP, N, I, HAVE, WAITING_JOBS, JOBS, FOR, WAITING_WORKERS, " \
                       "WAITING=waiting, WORKERS=workers]"

            @pytest.fixture
            def waiting_jobs_pattern():
                return "[LETTER, DATE, LEVEL, SEP, N, I, HAVE, WAITING_JOBS, JOBS, FOR, WAITING_WORKERS, " \
                       "WAITING=waiting, WORKERS=workers]"

            @pytest.fixture
            def waiting_workers_metric_value():
                return "$WAITING_WORKERS"

            @pytest.fixture
            def waiting_jobs_metric_value():
                return "$WAITING_JOBS"

            @pytest.fixture
            def log_metric_filters(waiting_workers_pattern, waiting_jobs_pattern,
                                   waiting_workers_metric_value, waiting_jobs_metric_value):
                return [
                    {
                        "pattern": waiting_workers_pattern,
                        "metric_transformation": {
                            "name": "waiting_workers",
                            "namespace": "Jobs",
                            "value": waiting_workers_metric_value,
                        }
                    },
                    {
                        "pattern": waiting_jobs_pattern,
                        "metric_transformation": {
                            "name": "waiting_jobs",
                            "namespace": "Jobs",
                            "value": waiting_jobs_metric_value,
                        }
                    }
                ]

            @pytest.fixture
            def component_kwargs(component_kwargs, log_metric_filters):
                component_kwargs["log_metric_filters"] = log_metric_filters
                return component_kwargs

            @pulumi.runtime.test
            def it_creates_metric_filters(sut):
                assert sut.log_metric_filters

            @pulumi.runtime.test
            def it_sets_the_workers_pattern(sut, waiting_workers_pattern):
                return assert_output_equals(sut.log_metric_filters[0].pattern, waiting_workers_pattern)

            @pulumi.runtime.test
            def it_sets_the_workers_metric_name(sut):
                return assert_output_equals(sut.log_metric_filters[0].metric_transformation.name,
                                            sut.project_stack + "-waiting_workers")

            @pulumi.runtime.test
            def it_sets_the_workers_values(sut, waiting_workers_metric_value):
                return assert_output_equals(sut.log_metric_filters[0].metric_transformation.value,
                                            waiting_workers_metric_value)

            @pulumi.runtime.test
            def it_sets_the_workers_namespace(sut):
                return assert_output_equals(sut.log_metric_filters[0].metric_transformation.namespace,
                                            "Jobs")

            @pulumi.runtime.test
            def it_sets_the_jobs_pattern(sut, waiting_jobs_pattern):
                return assert_output_equals(sut.log_metric_filters[1].pattern, waiting_jobs_pattern)

            @pulumi.runtime.test
            def it_sets_the_jobs_metric_name(sut):
                return assert_output_equals(sut.log_metric_filters[1].metric_transformation.name,
                                            sut.project_stack + "-waiting_jobs")

            @pulumi.runtime.test
            def it_sets_the_jobs_values(sut, waiting_jobs_metric_value):
                return assert_output_equals(sut.log_metric_filters[1].metric_transformation.value,
                                            waiting_jobs_metric_value)

            @pulumi.runtime.test
            def it_sets_the_jobs_namespace(sut):
                return assert_output_equals(sut.log_metric_filters[1].metric_transformation.namespace,
                                            "Jobs")

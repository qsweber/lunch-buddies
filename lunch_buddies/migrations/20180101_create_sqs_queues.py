import boto3

from lunch_buddies.lib.service_context import service_context
from lunch_buddies.constants.stages import Stage


def migrate():
    sqs = boto3.client("sqs")

    for stage in [Stage.PROD, Stage.DEV]:
        for queue_name in []:
            queue_stage_name = service_context.clients.sqs_v2._name_for_queue_stage(
                queue_name, stage
            )

            print(queue_stage_name)
            queue = sqs.create_queue(QueueName=queue_stage_name)
            print(queue["QueueUrl"])

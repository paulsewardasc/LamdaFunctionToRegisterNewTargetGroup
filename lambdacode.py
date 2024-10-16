import boto3
import time
import os

# Create clients for ELBv2 and SSM
elbv2_client = boto3.client('elbv2')
ssm_client = boto3.client('ssm')

def lambda_handler(event, context):
    # Retrieve ALB names from Parameter Store
    src_alb = get_parameter('k8s-producti-llmapi-internal-name')
    tgt_alb = get_parameter('k8s-producti-llmapi-external-name')


    # Get Source ALB Target IP
    sip = get_target_ip(src_alb)

    # Get Target ALB Target IP
    tip = get_target_ip(tgt_alb)

    # Get Target ALB Target Group ARN
    tarn = get_target_group_arn(tgt_alb)

    if sip != tip:
        print(f"A new server has been found {sip}, updating External Target Group")
        register_target(tarn, sip)
        time.sleep(10)  # Wait for registration to propagate

        # Get old target IP (assuming it's now at index 1 after new registration)
        old_tip = get_target_ip(tgt_alb, target_index=1) 
        print(old_tip)
        deregister_target(tarn, old_tip)
    else:
        print(f"The servers match: {sip}, {tip}")

def get_parameter(parameter_name):
    """Retrieves a parameter value from AWS Parameter Store."""
    try:
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Error getting parameter {parameter_name}: {e}")
        return None

def get_target_group_arn(alb_name):
    """Retrieves the Target Group ARN associated with the given ALB."""
    try:
        response = elbv2_client.describe_load_balancers(Names=[alb_name])
        alb_arn = response['LoadBalancers'][0]['LoadBalancerArn']

        response = elbv2_client.describe_target_groups(LoadBalancerArn=alb_arn)
        target_group_arn = response['TargetGroups'][0]['TargetGroupArn']
        return target_group_arn
    except Exception as e:
        print(f"Error getting Target Group ARN: {e}")
        return None

def get_target_ip(alb_name, target_index=0):
    """Retrieves the IP address of the registered target for the given ALB."""
    try:
        target_group_arn = get_target_group_arn(alb_name)
        if target_group_arn:
            response = elbv2_client.describe_target_health(TargetGroupArn=target_group_arn)
            target_ip = response['TargetHealthDescriptions'][target_index]['Target']['Id']
            return target_ip
        else:
            return None
    except Exception as e:
        print(f"Error getting Target IP: {e}")
        return None

def register_target(target_group_arn, target_ip):
    """Registers the given target IP with the specified Target Group."""
    try:
        elbv2_client.register_targets(
            TargetGroupArn=target_group_arn,
            Targets=[{'Id': target_ip}]
        )
    except Exception as e:
        print(f"Error registering target: {e}")

def deregister_target(target_group_arn, target_ip):
    """Deregisters the given target IP from the specified Target Group."""
    try:
        elbv2_client.deregister_targets(
            TargetGroupArn=target_group_arn,
            Targets=[{'Id': target_ip}]
        )
    except Exception as e:
        print(f"Error deregistering target: {e}")

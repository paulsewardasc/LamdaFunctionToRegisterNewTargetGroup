# LamdaFunctionToRegisterNewTargetGroup
Create a lambda function to update a registered target in a Target Group when another Target Group (Internal) is updated.

We have an internal load balancer that is updated by Terraform, when this changes we want the external load balancer to be updated with the new server in the internal target group.

An bash script to do this would be:

#Notes:
#SRC_ALB is defined as an environmental variable for the source ALB
#TGT_ALC is defined as an environmental variable for the target ALB
#SIP is the registered target in the Soruce ALB
#TIP is the registered target in the target ALB
#OLD_TIP is the old IP address after the update has been made

# Get the current IP Address from the internal load balancer
SIP=$(aws elbv2 describe-target-groups     --load-balancer-arn $(aws elbv2 describe-load-balancers --names $SRC_ALB --query 'LoadBalancers[*].LoadBalancerArn' --output text)  --query 'TargetGroups[*].TargetGroupArn' --output text | xargs -I {} aws elbv2 describe-target-health --target-group-arn {} --query 'TargetHealthDescriptions[0].Target.Id')

# Get the current IP Address from the external load balancer
TIP=$(aws elbv2 describe-target-groups     --load-balancer-arn $(aws elbv2 describe-load-balancers --names $TGT_ALB --query 'LoadBalancers[*].LoadBalancerArn' --output text)  --query 'TargetGroups[*].TargetGroupArn' --output text | xargs -I {} aws elbv2 describe-target-health --target-group-arn {} --query 'TargetHealthDescriptions[0].Target.Id')

# Check to see if any changes have been made
if [ "$SIP" != "$TIP" ]; then
  TARN=$(aws elbv2 describe-target-groups     --load-balancer-arn $(aws elbv2 describe-load-balancers --names $TGT_ALB --query 'LoadBalancers[*].LoadBalancerArn' --output text)     --query 'TargetGroups[0].TargetGroupArn')
  echo "A new server has been found $SIP, updating External Target Group"
  aws elbv2 register-targets --target-group-arn $TARN --targets Id=$SIP
  # Wait to the change to propogate, this may not bee needed
  sleep 10
  OLD_TIP=$(aws elbv2 describe-target-groups     --load-balancer-arn $(aws elbv2 describe-load-balancers --names $TGT_ALB --query 'LoadBalancers[*].LoadBalancerArn' --output text)  --query 'TargetGroups[*].TargetGroupArn' --output text | xargs -I {} aws elbv2 describe-target-health --target-group-arn {} --query 'TargetHealthDescriptions[1].Target.Id')
  echo $OLD_TIP
  deregister-targets --target-group-arn $TARN --targets Id=$OLD_TIP
else
  echo "The servers match: $SIP, $TIP"
fi

Steps:

1) Create a lambda function that pulls the names of the load balancers from Parameter Store, compares the IPs and updates the external lb if required (see lambdacode.py)
2) Create an AWS EventBridge function that will fire when it sees a "RegisterTargets" event in CloudTrail for "elasticloadbalancing.amazonaws.com"

e.g.
{
  "source": ["aws.elasticloadbalancing"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["elasticloadbalancing.amazonaws.com"],
    "eventName": ["RegisterTargets"],
    "requestParameters": {
      "targetGroupArn": ["arn:aws:elasticloadbalancing:REGION:ACCOUNT:targetgroup/TARGETGROUP"]
    }
  }
}

3) Make the EventBridge call the Lambda Function
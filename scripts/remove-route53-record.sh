#!/bin/bash 
#YC - 21/10/2021
#This script should be sourced
##################################################################
# Purpose: Remove route53 record
# Arguments:
#   
#   $1 -> AWS Profile
#   $2 -> AWS region
#   $3 -> Hosted Zone ID
#   $4 -> DNS record
##################################################################
function delete_route53_record()
{
    AWS_PROFILE=$1
    AWS_REGION=$2
    HOSTED_ZONE_ID=$3
    DNS_NAME=$4

    RECORD=$(aws --region $AWS_REGION --profile $AWS_PROFILE route53 list-resource-record-sets --hosted-zone-id=$HOSTED_ZONE_ID $PROFILE_PARAMETER | jq -r '.ResourceRecordSets[] | select (.Name == "'$DNS_NAME'.")')

    cat <<- EOF > /tmp/remove-53-payload
{
    "Comment": "Delete single record set",
    "Changes": [
        {
            "Action": "DELETE",
            "ResourceRecordSet": $RECORD
        }
    ]
}
EOF
    aws  --region $AWS_REGION --profile $AWS_PROFILE route53 change-resource-record-sets --hosted-zone-id=$HOSTED_ZONE_ID --change-batch file:///tmp/remove-53-payload
    rm /tmp/remove-53-payload
}

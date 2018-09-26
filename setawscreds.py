import sys
import os
import subprocess
import argparse
import configparser

MFASERIAL = 'mfa_serial'
CABUNDLE = 'ca_bundle'

parser = argparse.ArgumentParser()
parser.add_argument("--profile",help="The AWS credentials profile to use access keys",default='default')
parser.add_argument("--region",help="Override the AWS config region for api calls")
parser.add_argument("--mfa-token",help="The MFA token to use for credentials")
args = parser.parse_args()

config_path = os.path.expanduser('~\\.aws\config')
config = configparser.ConfigParser()
config.read(config_path)
isConfigDirty=False

profile = args.profile or 'default'
#per aws specification, profile must be 'profile <profile>' in config files
config_profile = profile != 'default' and 'profile' not in profile and "profile "+profile or profile

if config_profile not in config.sections():
    sys.exit("There is no profile section '{}' in the config file".format(config_profile));
    
if 'region' not in config[config_profile] and args.region == None:
    sys.exit("There is no region configured in your config file.\nPlease use the --region command option\nor run 'aws configure' to set it.")
   
region = args.region or config[config_profile]['region']

print("using profile '{}' in region '{}'".format(profile,region))

# get some EWS specific info and permanently store in our aws config (the are config spec items)
if MFASERIAL not in config[config_profile]:
    config[config_profile][MFASERIAL] = input("please input your {} AWS MFA ARN: ".format(profile.upper()))
    isConfigDirty = True
if CABUNDLE not in config[config_profile]:
    config[config_profile][CABUNDLE] = input("please input the path to your Certificate Bundle: ")
    isConfigDirty = True
    
if isConfigDirty:
    with open(config_path,"w") as fd:
        config.write(fd)
 
mfa_serial = config[config_profile][MFASERIAL] 
token = args.mfa_token or input("Please input your MFA token: ")
#print("arn: {}, token: {}".format(mfa_serial,token))

# some corporate necessary environment variables	  
os.environ["HTTPS_PROXY"] = "http://corpwproxy.ews.int:8080"
os.environ["HTTP_PROXY"] = "http://corpwproxy.ews.int:8080"	

"""
AWS CREDENTIALS SECTION 
"""
import boto3
session=boto3.Session(region_name=region,profile_name=profile)
sts = session.client('sts')
duration=(60*60*8)  #8 hours

credentials = sts.get_session_token(DurationSeconds=duration,SerialNumber=mfa_serial,TokenCode=token)

# set our temp credentials into the shell environment
os.environ["AWS_ACCESS_KEY_ID"] = credentials["Credentials"]["AccessKeyId"]	  
os.environ["AWS_SECRET_ACCESS_KEY"] = credentials["Credentials"]["SecretAccessKey"]	  
os.environ["AWS_SESSION_TOKEN"] = credentials["Credentials"]["SessionToken"]	  
# if the user is overriding the region, set it in the environment so it overrides the config setting
os.environ["AWS_DEFAULT_REGION"] = region

# a prompt to show us where we are  
os.environ["PROMPT"] = "(AWSMFA) $P$G"
	  
# execute a new shell
subprocess.run(os.environ['COMSPEC'])



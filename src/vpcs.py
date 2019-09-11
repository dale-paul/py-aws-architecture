import argparse
import boto3

parser = argparse.ArgumentParser()
parser.add_argument("--region",help="Override the AWS config region for api calls")
parser.add_argument("--vpcid",help="ID of VPC to dump, all VPC's if blank")
args = parser.parse_args()

session=boto3.Session(region_name=args.region)
ec2 = session.resource('ec2') #type 

def dump_vpcs():
    level = 0
    if args.vpcid:
        dump_vpc(ec2.Vpc(args.vpcid))
    else:
        for vpc in ec2.vpcs.all():
            dump_vpc(vpc)

def get_nameTag(obj):
    return next((i['Value'] for i in obj.tags if i['Key'] == 'Name'),None)

def dump_vpc(vpc):
    '''VPCs'''
    level = 0
    vpcFmt='{0}{1:25}{2}'
    print(vpcFmt.format('\t'*level,'VPC-ID','NAME'))
    name = get_nameTag(vpc) 
    name += '(default)' if vpc.is_default else ''
    print(vpcFmt.format('\t'*level,vpc.id,name))
    #dump default route table
    dump_route_tables(vpc.route_tables.filter(Filters=[{'Name':'association.main','Values': ['true']}]),level+1)
    #dump default Network ACLs
    dump_network_acls(vpc.network_acls.filter(Filters=[{'Name':'default','Values': ['true']}]),level+1)
    #dump subnets, routes and NACLs
    dump_subnets(vpc,level+1)
    #dump security groups
    dump_security_groups(vpc,level+1)
    print()
    #Note: need to find main (unassigned to routetable or NACL) route table and nacl and print under the VPC

def dump_subnets(vpc,level):
    '''SUBNETS'''
    # preload the routes so we can get the id's for our subnets
    routeTbls = vpc.route_tables.all()
    ### SUBNETS
    subnetFmt = '{0}{1:25}{2:30}{3:20}'
    print(subnetFmt.format('\t'*level,'SUBNET-ID','NAME','CIDR'))
    for subnet in vpc.subnets.all():
        nameTag = get_nameTag(subnet) 
        print(subnetFmt.format('\t'*level,subnet.id,nameTag,subnet.cidr_block))
        ### public network interfaces in this subnet
        ifaces = [e for e in subnet.network_interfaces.filter(Filters=[{'Name':'attachment.status','Values':['attached']}]) if e.association != None]
        if ifaces:
            level += 1
            netFmt='{0}{1:17}{2}'
            print(netFmt.format('\t'*level,'PUBLIC IP','PUBLIC DNS'))
            for i in ifaces:
                print(netFmt.format('\t'*level,i.association.public_ip,i.association.public_dns_name))
            level -= 1
        print()
        dump_route_tables(vpc.route_tables.filter(Filters=[{'Name':'association.subnet-id','Values': [subnet.id]}]),level+1)
        dump_network_acls(vpc.network_acls.filter(Filters=[{'Name':'association.subnet-id','Values': [subnet.id]}]),level+1)
    print()
 #   print('\t'*level,'-'*10,'\n')

def dump_route_tables(routeTbls,level):
    for rtbl in routeTbls:
        dump_route_table(rtbl,level)

def dump_route_table(rtbl,level):
    ### ROUTE TABLES 
    rtblFmt = '{0}{1:25}{2}'
    print(rtblFmt.format('\t'*level,'ROUTE-TABLE-ID','NAME'))
    nameTag = get_nameTag(rtbl) 
    print(rtblFmt.format('\t'*level,rtbl.id,nameTag or ''))
    ### ROUTES
    level += 1
    routeFmt = '{0}{1:20}{2:25}{3:10}'
    print(routeFmt.format('\t'*level,'DESTINATION', 'TARGET', 'STATUS'))
    for rte in rtbl.routes:
        tgt = rte.gateway_id or rte.instance_id or rte.nat_gateway_id or rte.network_interface_id or rte.vpc_peering_connection_id or rte.transit_gateway_id or rte.egress_only_internet_gateway_id
        print(routeFmt.format('\t'*level, rte.destination_cidr_block, tgt, rte.state))
    print()

def dump_network_acls(acls,level):
    for acl in acls:
        dump_network_acl(acl,level)

def dump_network_acl(acl,level):
    ### ACL's associated with subnet
    nameTag = get_nameTag(acl) 
    aclFmt = '{0}{1:25}{2}'
    print(aclFmt.format('\t'*level,'NETWORK-ACL-ID','NAME'))
    print(aclFmt.format('\t'*level,acl.id,nameTag))
    ### Entries
    entries = sorted(acl.entries, key = lambda i: (i['Egress'],i['RuleNumber']))
    if entries:
        level += 1
        entryFmt = '{0}{1:<12}{2:>10}{3:>10}{4:>12}{5:>22}{6:>12}'
        print(entryFmt.format('\t'*level,'RULE','RULE #','PROTOCOL','PORT RANGE','SOURCE','ALLOW/DENY'))
        for entry in entries:
            rule = 'OUTBOUND' if entry['Egress'] == True else 'INBOUND'
            ruleNum = '*' if entry['RuleNumber'] == 32767 else entry['RuleNumber']
            dictProtocol = {
                '6' : 'TCP',
                '17' : 'UDP',
                '1' : 'ICMP'
            }
            proto = dictProtocol.get(entry['Protocol'],'ALL')
            ports = entry.get('PortRange',{})
            pFrom = ports.get('From','ALL')
            pTo = ports.get('To','ALL')
            #needs work for entry['IcmpTypeCode'] with keys 'Code' and 'Type' for pRange instead of ports
            pRange = '{}-{}'.format(pFrom,pTo) if pFrom != pTo else pFrom if pFrom == 'ALL' else pFrom
            print(entryFmt.format('\t'*level,rule,ruleNum,proto,pRange,entry['CidrBlock'],entry['RuleAction'].upper()))
    print()

def dump_security_groups(vpc,level):
    sgFmt = '{0}{1:25}{2}'
    permFmt = '{0}{1:10}{2:15}{3}'
    print(sgFmt.format('\t'*level,'SEC-GROUP-ID','GROUP NAME'))
    for grp in vpc.security_groups.all():
        print(sgFmt.format('\t'*level,grp.id,grp.group_name))
        level += 1
        if grp.ip_permissions:
            print("{0}INBOUND".format('\t'*level))
            level += 1
            print(permFmt.format('\t'*level,'PROTOCOL','PORT','SOURCE'))
            for perm in grp.ip_permissions:
                protocol = 'ALL' if perm['IpProtocol'] == '-1' else perm['IpProtocol']
                cidrList = [r['CidrIp'] for r in perm['IpRanges']]
                grpList = [r['GroupId'] for r in perm['UserIdGroupPairs']]
                iterList = cidrList or grpList
                if protocol == 'ALL':
                    port = 'ALL'
                else:
                    port = perm['FromPort'] if perm['FromPort'] == perm['ToPort'] else '{}-{}'.format(perm['FromPort'],perm['ToPort'])
                for x in iterList:
                    print(permFmt.format('\t'*level,protocol,str(port),x))
            level -= 1
        if grp.ip_permissions_egress:
            print("{0}OUTBOUND".format('\t'*level))
            level += 1
            print(permFmt.format('\t'*level,'PROTOCOL','PORT','SOURCE'))
            for perm in grp.ip_permissions_egress:
                protocol = 'ALL' if perm['IpProtocol'] == '-1' else perm['IpProtocol']
                cidrList = [r['CidrIp'] for r in perm['IpRanges']]
                grpList = [r['GroupId'] for r in perm['UserIdGroupPairs']]
                iterList = cidrList or grpList
                if protocol == 'ALL':
                    port = 'ALL'
                else:
                    port = perm['FromPort'] if perm['FromPort'] == perm['ToPort'] else '{}-{}'.format(perm['FromPort'],perm['ToPort'])
                for x in iterList:
                    print(permFmt.format('\t'*level,protocol,str(port),x))
            level -= 1
        level -= 1
        print()
    print()

def main():
    dump_vpcs()

    
if __name__ == "__main__":
    main()
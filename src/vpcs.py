import argparse
import boto3

parser = argparse.ArgumentParser()
parser.add_argument("--region",help="Override the AWS config region for api calls")
args = parser.parse_args()

session=boto3.Session(region_name=args.region)
ec2 = session.resource('ec2') #type 

def dump_vpcs(level):
    '''VPCs'''
    vpcFmt='{0}{1:25}{2:30}{3}'
    print(vpcFmt.format('\t'*level,'VPC-ID','NAME','CIDR'))
    for vpc in ec2.vpcs.all():
        name = [ x['Value'] for x in (d for d in vpc.tags if 'Name' in d['Key'] )][0]
        name += '(default)' if vpc.is_default else ''
        print(vpcFmt.format('\t'*level,vpc.id,name,vpc.cidr_block))
        dump_subnets(vpc,level+1)
        dump_security_groups(vpc,level+1)
    print()

def dump_subnets(vpc,level):
    '''SUBNETS'''
    # preload the routes so we can get the id's for our subnets
    routeTbls = vpc.route_tables.all()
    ### SUBNETS
    subnetFmt = '{0}{1:25}{2:30}{3:20}'
    print(subnetFmt.format('\t'*level,'SUBNET-ID','NAME','CIDR'))
    for subnet in vpc.subnets.all():
        nameTag = next((i['Value'] for i in subnet.tags if i['Key'] == 'Name'),None)
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
        for rtbl in routeTbls.filter(Filters=[{'Name':'association.subnet-id','Values': [subnet.id]}]):
            dump_route_tables(subnet,rtbl,level+1)
    print()
 #   print('\t'*level,'-'*10,'\n')

def dump_route_tables(subnet,rtbl,level):
    ### ROUTE TABLES 
    rtblFmt = '{0}{1:25}{2}'
    print(rtblFmt.format('\t'*level,'ROUTE-TABLE-ID','NAME'))
    nameTag = next((i['Value'] for i in rtbl.tags if i['Key'] == 'Name'),None)
    print(rtblFmt.format('\t'*level,rtbl.id,nameTag or ''))

    ### ROUTES
    level += 1
    routeFmt = '{0}{1:20}{2:25}{3:10}'
    print(routeFmt.format('\t'*level,'DESTINATION', 'TARGET', 'STATUS'))
    for rte in rtbl.routes:
        tgt = rte.gateway_id or rte.instance_id or rte.nat_gateway_id or rte.network_interface_id or rte.vpc_peering_connection_id or rte.transit_gateway_id or rte.egress_only_internet_gateway_id
        print(routeFmt.format('\t'*level, rte.destination_cidr_block, tgt, rte.state))
    print()
    # level -= 1
    # print('\t'*level,'-'*10,'\n')

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
    # print('\t'*level,'-'*10,'\n')

def dummy():
    dump_vpcs(0)

def dummy2():
    """ VPCs """
    level=0
    vpcFmt='{0}{1:25}{2:30}{3}'
    print(vpcFmt.format('\t'*level,'VPC-ID','NAME','CIDR'))
    for vpc in ec2.vpcs.all():
        name = [ x['Value'] for x in (d for d in vpc.tags if 'Name' in d['Key'] )][0]
        name += '(default)' if vpc.is_default else ''
        print(vpcFmt.format('\t'*level,vpc.id,name,vpc.cidr_block))
        level += 1

        # preload the routes so we can get the id's for our subnets
        routeTbls = vpc.route_tables.all()
        ### SUBNETS
        subnetFmt = '{0}{1:25}{2:30}{3:20}{4}'
        print(subnetFmt.format('\t'*level,'SUBNET-ID','NAME','CIDR','Route Table'))
        for subnet in vpc.subnets.all():
            nameTag = next((i['Value'] for i in subnet.tags if i['Key'] == 'Name'),None)
            rid = next((r.id for r in routeTbls.filter(Filters=[{'Name':'association.subnet-id','Values': [subnet.id]}])),'None')
            print(subnetFmt.format('\t'*level,subnet.id,nameTag,subnet.cidr_block,rid))
            ### public network interfaces in this subnet
            ifaces = [e for e in subnet.network_interfaces.filter(Filters=[{'Name':'attachment.status','Values':['attached']}]) if e.association != None]
            if ifaces:
                level += 1
                #print('\t'*level,'PUBLIC NETWORK INTERFACES')
                netFmt='{0}{1:17}{2}'
                print(netFmt.format('\t'*level,'PUBLIC IP','PUBLIC DNS'))
                for i in ifaces:
                    print(netFmt.format('\t'*level,i.association.public_ip,i.association.public_dns_name))
                level -= 1
        print('\t'*level,'-'*10,'\n')
        
        ### ROUTE TABLES 
        rtblFmt = '{0}{1:25}{2}'
        print(rtblFmt.format('\t'*level,'ROUTE-TABLE-ID','NAME'))
        for rtbl in routeTbls:
            nameTag = next((i['Value'] for i in rtbl.tags if i['Key'] == 'Name'),None)
            print(rtblFmt.format('\t'*level,rtbl.id,nameTag or ''))
        
            ### ROUTES
            level += 1
            routeFmt = '{0}{1:20}{2:25}{3:10}'
            print(routeFmt.format('\t'*level,'DESTINATION', 'TARGET', 'STATUS'))
            for rte in rtbl.routes:
               tgt = rte.gateway_id or rte.instance_id or rte.nat_gateway_id or rte.network_interface_id or rte.vpc_peering_connection_id or rte.transit_gateway_id or rte.egress_only_internet_gateway_id
               print(routeFmt.format('\t'*level, rte.destination_cidr_block, tgt, rte.state))
            level -= 1
        print('\t'*level,'-'*10,'\n')
            
        ### SECURITY GROUPS
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
        print('\t'*level,'-'*10,'\n')
        
        level -= 1

def main():
    dummy()
    
if __name__ == "__main__":
    main()
from django.db import models
from apps.ava_core.models import TimeStampedModel
from apps.ava_core_org.models import Organisation, OrganisationGroup, GroupIdentifier
from apps.ava_core_people.models import Identifier, Person
#from apps.ava_core_identity.models import Identity
from django.utils.html import escape
from django.contrib.auth.models import User
from ldap import *
import ldif, sys, json
from StringIO import StringIO
from ldap.cidict import cidict


#from django.core.exceptions import DoesNotExist

class ActiveDirectoryUser(TimeStampedModel):
    dn = models.CharField(max_length = 300)
    accountExpires = models.CharField(max_length = 300)
    adminCount = models.CharField(max_length = 300)
    badPasswordTime = models.CharField(max_length = 300)
    badPwdCount = models.CharField(max_length = 300)
    cn = models.CharField(max_length = 300)
    description = models.CharField(max_length = 300)
    displayName = models.CharField(max_length = 300)
    distinguishedName = models.CharField(max_length = 300)
    isCriticalSystemObject = models.CharField(max_length = 300)
    lastLogoff = models.CharField(max_length = 300)
    lastLogon = models.CharField(max_length = 300)
    lastLogonTimestamp = models.CharField(max_length = 300)
    logonCount = models.CharField(max_length = 300)
    logonHours = models.CharField(max_length = 300)
    name = models.CharField(max_length = 300)
    objectGUID = models.CharField(max_length = 300)
    objectSid = models.CharField(max_length = 300)
    primaryGroupID = models.CharField(max_length = 300)
    pwdLastSet = models.CharField(max_length = 300)
    sAMAccountName = models.CharField(max_length = 300)
    sAMAccountType = models.CharField(max_length = 300)
    uSNChanged = models.CharField(max_length = 300)
    uSNCreated = models.CharField(max_length = 300)
    userAccountControl = models.CharField(max_length = 300)
    whenChanged = models.CharField(max_length = 300)
    whenCreated = models.CharField(max_length = 300)
    memberOf = models.ManyToManyField('ActiveDirectoryGroup') 
    user = models.ForeignKey(User) 
    queryParameters = models.ForeignKey('QueryParameters')
    #identity = models.ForeignKey('ava_core_identity.Identity',null=True,blank=True)

    def __unicode__(self):
        return self.name or u''

    class Meta:
        unique_together = ('objectGUID','objectSid')

class ActiveDirectoryGroup(TimeStampedModel):
    cn = models.CharField(max_length = 300)
    distinguishedName = models.CharField(max_length = 300, unique=True)
    name = models.CharField(max_length = 100)
    objectCategory = models.CharField(max_length = 300)
    sAMAccountName = models.CharField(max_length = 300)
    objectGUID = models.CharField(max_length = 300)
    objectSid = models.CharField(max_length = 300)
    member = models.ManyToManyField('ActiveDirectoryUser')
    user = models.ForeignKey(User) 
    queryParameters = models.ForeignKey('QueryParameters')
    #identity = models.ForeignKey('ava_core_identity.Identity',null=True,blank=True)

    def __unicode__(self):
        return self.cn or u''

    class Meta:
        unique_together = ('objectGUID','objectSid')

class QueryParameters(TimeStampedModel):
    #user_dn = "cn=Administrator,cn=Users,dc=ava,dc=test,dc=domain"
    #user_pw = "Password1"
    #dump_dn = "dc=ava,dc=test,dc=domain"
    #server = 'ldap://dc.ava.test.domain'
    user_dn = models.CharField(max_length = 100, verbose_name='User')
    user_pw = models.CharField(max_length = 100, verbose_name='Password')
    dump_dn = models.CharField(max_length = 100, verbose_name='Domain')
    server = models.CharField(max_length = 100, verbose_name='Server')
    organisation = models.ForeignKey('ava_core_org.Organisation')
    user = models.ForeignKey(User, null=False)    

    def __unicode__(self):
        return self.server or u''
    
    class Meta:
        unique_together=('user','server','user_dn')

class ActiveDirectoryHelper():
    

    def getConnection(self, parameters):
        try:
            connection = initialize(parameters.server)
            #print "user_dn = "+parameters.user_dn+" user_pw="+parameters.user_pw+"\n"
            connection.set_option(OPT_REFERRALS, 0)    
            connection.simple_bind_s(parameters.user_dn, parameters.user_pw)
            #print (connection.whoami_s())
            return connection

        except LDAPError, e:
            if type(e.message) == dict:
                for (k, v) in e.message.iteritems():
                    sys.stderr.write("%s: %sn" % (k, v))
                    sys.stderr.write("\n")
            else:
                sys.stderr.write(e.message)
                sys.exit(1)
   
    
    def search(self, parameters, filter, attrs):
        connection = self.getConnection(parameters)
        results = connection.search_s(parameters.dump_dn, SCOPE_SUBTREE, filter,attrs)
        res = []

        if type(results) == tuple and len(results) == 2:
            (code, arr) = results
        elif type(results) == list:
            arr = results

        if len(results) == 0:
            return res

        for item in arr:
            res.append(LDAPSearchResult(item))

        ret_res = []
        for record in res:
            ret_res.append(record.to_ldif())

        connection.unbind()
        return res
    
    def getAll(self,parameters,user):
        #print "Getting groups"
        self.getGroups(parameters,user)
        #print "Getting users"
        self.getUsers(parameters,user)
        #print "Getting groups"
        self.getGroups(parameters,user)

    def getGroups(self,parameters,user,organisation):
        filter = '(objectclass=group)'
        attrs = ['cn','distinguishedName','name','objectCategory','sAMAccountName','objectGUID','objectSid','member']
        results = self.search(parameters,filter,attrs)
        for  v in results:
            new_attrs = {}
            users = []
            fishes = []
            new_attrs.update(v.get_attributes())
            for key, value in new_attrs.iteritems():
                if len(value) >  0:
                    value = ' '.join(value)
                    valid_utf8 = True
                    try:
                        value.decode('utf-8')
                    except UnicodeDecodeError:
                        valid_utf8 = False

                    if valid_utf8:
                        new_attrs[key] = value
                        if key == 'member':
                            user_cn = value.split(' CN=')
                            for cn in user_cn:
                                if not cn.startswith('CN='):
                                    cn = "CN="+cn
                                qs=ActiveDirectoryUser.objects.filter(user=user,queryParameters=parameters,distinguishedName=cn).first()
                                if qs:
                                    users.append(qs)
                    else:
                        new_attrs[key] = self.cleanhex(value)
            
            new_attrs.pop('member',None)
            rows = ActiveDirectoryGroup.objects.filter(**new_attrs).count()
            if rows == 0:
                ad_group = ActiveDirectoryGroup.objects.create(queryParameters=parameters,user=user,**new_attrs)
                OrganisationGroup.objects.get_or_create(name=ad_group.cn, grouptype=OrganisationGroup.AD,organisation=organisation)
                ad_group.member.add(*users)
                ad_group.save()

    def cleanhex(self,val):
        s = ['\\%02X' % ord(x) for x in val] 
        return ''.join(s)

    def getUsers(self,parameters,user):
        filter = '(objectclass=user)'
        attrs = ['dn','accountExpires','adminCount','badPasswordTime','badPwdCount','cn','description','displayName','isCriticalSystemObject','lastLogoff','lastLogon','lastLogonTimestamp','logonCount','logonHours','name','objectGUID','objectSid','primaryGroupID','pwdLastSet','sAMAccountName','sAMAccountType','uSNChanged','uSNCreated','userAccountControl','whenChanged','whenCreated','memberOf','distinguishedName']
        results = self.search(parameters,filter,attrs)
        for  v in results:
            new_attrs = {}
            groups = []
            org_groups = []
            new_attrs.update(v.get_attributes())
            for key, value in new_attrs.iteritems():
                if len(value) >  0:
                    value = ' '.join(value)
                    valid_utf8 = True
                    try:
                        value.decode('utf-8')
                    except UnicodeDecodeError:
                        valid_utf8 = False

                    if valid_utf8:
                        new_attrs[key] = value
                        if key == 'memberOf':
                            group_cn = value.split(' CN=')
                            for cn in group_cn:
                                if not value.startswith('CN='):
                                    cn = "CN="+cn
                                qs = ActiveDirectoryGroup.objects.filter(user=user,queryParameters=parameters,cn=cn).first()
                                if qs:
                                    groups.append(qs)
                    else:
                        new_attrs[key] = self.cleanhex(value)
            
            new_attrs.pop('memberOf',None)
            rows = ActiveDirectoryUser.objects.filter(**new_attrs).count()
            if rows == 0:
                ad_user = ActiveDirectoryUser.objects.create(queryParameters=parameters,user=user,**new_attrs)
                Identifier.objects.get_or_create(identifier=ad_user.sAMAccountName, identifiertype=Identifier.UNAME)
                Identifier.objects.get_or_create(identifier=ad_user.sAMAccountName+"@avasecure.com", identifiertype=Identifier.EMAIL)
                ad_user.memberOf.add(*groups)
                ad_user.save()
    

class LDAPSearchResult:
    dn = ''
    attrs = {}
    page_size = 10

    def __init__(self, entry_tuple):
        (dn, attrs) = entry_tuple
        if dn:
            self.dn = dn
        else:
            return
    
        self.attrs = cidict(attrs)


    def get_attributes(self):
        return self.attrs


    def set_attributes(self, attr_dict):
        self.attrs = cidict(attr_dict)


    def has_attribute(self, attr_name):
        return self.attrs.has_key(attr_name)


    def get_attr_values(self, key):
        return self.attrs[key]


    def get_attr_names(self):
        return self.attrs.keys()


    def get_dn(self):
        return self.dn


    def pretty_print(self):
        str = "DN: " + self.dn + "\n"
        for a, v_list in self.attrs.iteritems():
            str = str + "Name: " + a + "\n"
        for v in v_list:
            str = str + " Value: " + v + "\n"
            str = str + "========"
        return str


    def to_ldif(self):
        out = StringIO()
        ldif_out = ldif.LDIFWriter(out)
        newdata = {}
        if hasattr(self, 'attrs'):
            newdata.update(self.attrs)
        ldif_out.unparse(self.dn, newdata)
        return out.getvalue()


class ExportLDAP():
    def generateGraph(self,parameters):
        node_results = self.nodes(parameters)
        return self.edges(node_results)
    
    def nodes(self, parameters):
        nodes = []
        elements = []
        ldap_users = ActiveDirectoryUser.objects.filter(queryParameters=parameters)
        fields = ['id','accountExpires','adminCount','name','isCriticalSystemObject','lastLogon','logonCount','pwdLastSet']
        for user in ldap_users:
            elements.append(user)
            current = self.model_to_dict(user,fields)
            current['name']=escape(current['name'])
            current['node_type'] = 'user'
            nodes.append(current)
        
        ldap_groups = ActiveDirectoryGroup.objects.filter(queryParameters=parameters)
        g = ['cn','member']
        for group in ldap_groups:
                current = self.model_to_dict(group,g)
                current['node_type'] = 'group'
                #if(hide == True and group.member.count() > 0):
                nodes.append(current)
                elements.append(group)
                #else:
                #    if(hide == False):
                #        nodes.append(current)
                #        elements.append(group)
        
        results = {}
        results['elements'] = elements
        results['nodes'] = nodes
        return results        
        
    def edges(self,results):
        elements = results['elements']
        nodes = results['nodes']
        
        edges = []
        for index, value in enumerate(elements):
            if isinstance(value,ActiveDirectoryGroup):
                users = value.member.all()
                for user in users:
                    current_edge = {}
                    user_index = elements.index(user)
                    current_edge['value'] = 'edge'+str(user_index)+"_"+str(index)
                    current_edge['source'] = user_index
                    current_edge['target'] = index
                    edges.append(current_edge)
            
        json_object = {}
        json_object['nodes'] = nodes;
        json_object['links'] = edges;
        j_out = json.dumps(json_object)
        return j_out

    def model_to_dict(self,instance, fields=None, exclude=None):
        """
        Returns a dict containing the data in ``instance`` suitable for passing as
        a Form's ``initial`` keyword argument.
    
        ``fields`` is an optional list of field names. If provided, only the named
        fields will be included in the returned dict.
    
        ``exclude`` is an optional list of field names. If provided, the named
        fields will be excluded from the returned dict, even if they are listed in
        the ``fields`` argument.
        """
        # avoid a circular import
        from django.db.models.fields.related import ManyToManyField
        opts = instance._meta
        data = {}
        for f in opts.concrete_fields + opts.virtual_fields + opts.many_to_many:
            if not getattr(f, 'editable', False):
                continue
            if fields and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
            if isinstance(f, ManyToManyField):
                # If the object doesn't have a primary key yet, just use an empty
                # list for its m2m fields. Calling f.value_from_object will raise
                # an exception.
                if instance.pk is None:
                    data[f.name] = []
                else:
                    # MultipleChoiceWidget needs a list of pks, not object instances.
                    qs = f.value_from_object(instance)
                    if qs._result_cache is not None:
                        data[f.name] = [item.pk for item in qs]
                    else:
                        data[f.name] = list(qs.values_list('pk', flat=True))
            else:
                data[f.name] = f.value_from_object(instance)
        return data

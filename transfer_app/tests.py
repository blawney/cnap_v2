import sys
from Crypto.Cipher import DES
import base64

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings

from transfer_app.models import Resource, Transfer, TransferCoordinator

# a method for creating a reasonable test dataset:
def create_data(testcase_obj):

    # create two users-- one is admin, other is regular
    testcase_obj.regular_user = get_user_model().objects.create_user(email='reguser@gmail.com', password='abcd123!')
    testcase_obj.admin_user = get_user_model().objects.create_user(email='admin@admin.com', password='abcd123!', is_staff=True)
    testcase_obj.other_user = get_user_model().objects.create_user(email='otheruser@gmail.com', password='abcd123!')

    # create a couple of Resources owned by admin:
    r1 = Resource.objects.create(
        source = 'google_bucket',
        path='gs://a/b/admin_owned1.txt',
        size=500,
        owner=testcase_obj.admin_user,
    )

    r2 = Resource.objects.create(
        source='google_storage',
        path='in some user dropbox',
        size=500,
        owner=testcase_obj.admin_user,
    )

    # create a couple of resources owned by the regular user:
    r3 = Resource.objects.create(
        source='google_storage',
        path='gs://a/b/reg_owned1.txt',
        size=500,
        owner=testcase_obj.regular_user,
    )
    r4 = Resource.objects.create(
        source='google_storage',
        path='gs://a/b/reg_owned2.txt',
        size=500,
        owner=testcase_obj.regular_user,
    )

    r5 = Resource.objects.create(
        source='google_storage',
        path='in some user dropbox',
        size=500,
        owner=testcase_obj.regular_user,
    )

    # create a batch of Transfers:
    tc1 = TransferCoordinator.objects.create()

    tc2 = TransferCoordinator.objects.create()

    tc3 = TransferCoordinator.objects.create()

    tc4 = TransferCoordinator.objects.create()

    # create Transfer instances for the Resources above
    # An admin-owned download transfer
    t1 = Transfer.objects.create(
        download=True,
        resource = r1,
        destination = 'dropbox',
        coordinator = tc1,
        originator = testcase_obj.admin_user
    )

    # Create two downloads and one upload owned by a regular user:
    t2 = Transfer.objects.create(
        download=True,
        resource = r3,
        destination = 'dropbox',
        coordinator = tc2,
        originator = testcase_obj.regular_user
    )
    t3 = Transfer.objects.create(
        download=True,
        resource = r4,
        destination = 'dropbox',
        coordinator = tc2,
        originator = testcase_obj.regular_user
    )

    t4 = Transfer.objects.create(
        download=False,
        resource = r5,
        destination = 'our system',
        coordinator = tc3,
        originator = testcase_obj.regular_user
    )

    # now create a Transfer that was originated by an admin, but the Resource is owned by
    # a regular user
    t5 = Transfer.objects.create(
        download=False,
        resource = r5,
        destination = 'our system',
        coordinator = tc4,
        originator = testcase_obj.admin_user
    )


# Tests related to Resource listing/creation/retrieval:

'''
Tests for listing Resources:
  -lists all Resources for admin user
  -lists Resources specific to a non-admin user
  - only admin can access the UserResourceList endpoint
    which allows admins to query all Resource objects owned by
    a particular user
'''
class ResourceListTestCase(TestCase):
    def setUp(self):
        create_data(self)

    def test_admin_can_list_all_resources(self):
        r = Resource.objects.all()
        client = APIClient()
        client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('resource-list')
        response = client.get(url)
        self.assertEqual(response.status_code,200) 
        self.assertEqual(len(response.data), len(r))

    def test_regular_user_can_list_only_their_resources(self):
        client = APIClient()
        client.login(email='reguser@gmail.com', password='abcd123!')
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk
        url = reverse('resource-list')
        response = client.get(url)
        data = response.data

        # test that we received 200, there are two resources, and they both
        # are owned by the 'regular' user
        self.assertEqual(response.status_code,200) 
        self.assertEqual(len(response.data), 3)
        self.assertTrue(all([x.get('owner') == reguser_pk for x in data]))

    def test_unauthenticated_user_gets_403_for_basic_list(self):
        client = APIClient()
        url = reverse('resource-list')
        response = client.get(url)
        self.assertEqual(response.status_code, 403)

'''

Tests for creation of Resource:
  - Admin user can create Resource for themself
  - Non-admin user can create Resource for themself
  - Admin user can create Resource for someone else
  - Non-admin user is blocked from creating Resource
    for others
'''
class ResourceCreateTestCase(TestCase):
    def setUp(self):
        self.regular_user = get_user_model().objects.create_user(email='reguser@gmail.com', password='abcd123!')
        self.admin_user = get_user_model().objects.create_user(email='admin@admin.com', password='abcd123!', is_staff=True)

    def test_admin_can_create_resource_for_self(self):
        # establish the admin client:
        client = APIClient()
        client.login(email='admin@admin.com', password='abcd123!')

        # get the admin user's pk:
        u = get_user_model().objects.filter(email='admin@admin.com')[0]
        adminuser_pk = u.pk
        url = reverse('resource-list')
        data = {'source': 'google_bucket', \
                'path': 'gs://foo/bar/baz.txt', \
                'name': 'baz.txt', \
                'size':500, \
                'owner': adminuser_pk, \
                'is_active': True,
                'expiration_date': '2018-12-02T00:00:00'
        }
        response = client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)  

        r = Resource.objects.all()
        self.assertEqual(len(r), 1)
        self.assertTrue(all([x.get_owner() == u for x in r]))

    def test_admin_can_create_resource_for_other(self):
        # establish the admin client:
        client = APIClient()
        client.login(email='admin@admin.com', password='abcd123!')

        # get the regular user's pk:
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk
        url = reverse('resource-list')
        data = {'source': 'google_bucket', \
                'path': 'gs://foo/bar/baz.txt', \
                'name': 'baz.txt', \
                'size':500, \
                'owner': reguser_pk, \
                'is_active': True,
                'expiration_date': '2018-12-02T00:00:00'
        }
        response = client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)  

        r = Resource.objects.all()
        self.assertEqual(len(r), 1)
        self.assertTrue(all([x.get_owner() == u for x in r]))

    def test_regular_user_can_create_resource_for_self(self):
        # establish the regular client:
        client = APIClient()
        client.login(email='reguser@gmail.com', password='abcd123!')

        # initial number of Resource objects:
        r_orig = Resource.objects.all()
        r_orig_len = len(r_orig)

        # get the regular user's pk:
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk
        url = reverse('resource-list')
        data = {'source': 'google_bucket', \
                'path': 'gs://foo/bar/baz.txt', \
                'name': 'baz.txt', \
                'size':500, \
                'owner': reguser_pk, \
                'is_active': True,
                'expiration_date': '2018-12-02T00:00:00'
        }
        response = client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)  

        r = Resource.objects.all()
        self.assertEqual(r_orig_len + 1, len(r))
        self.assertTrue(all([x.get_owner() == u for x in r]))

    def test_regular_user_cannot_create_resource_for_other(self):
        # establish the regular client:
        client = APIClient()
        client.login(email='reguser@gmail.com', password='abcd123!')

        # initial number of Resource objects:
        r_orig = Resource.objects.all()

        # get the admin user's pk:
        u = get_user_model().objects.filter(email='admin@admin.com')[0]
        adminuser_pk = u.pk
        url = reverse('resource-list')
        data = {'source': 'google_bucket', \
                'path': 'gs://foo/bar/baz.txt', \
                'name': 'baz.txt', \
                'size':500, \
                'owner': adminuser_pk, \
                'is_active': True,
                'expiration_date': '2018-12-02T00:00:00'
        }
        response = client.post(url, data, format='json')
        self.assertEqual(response.status_code, 404)  

        r = Resource.objects.all()
        self.assertEqual(len(r_orig), len(r))



'''
Test for listing specific Resource:
  - returns 404 if the pk does not exist regardless of user
  - returns 404 if a non-admin user requests a Resource
    owned by someone else
  - returns correctly if admin requests Resource owned by someone else
  - returns correctly if admin requests Resource owned by themself
'''
class ResourceDetailTestCase(TestCase):
    def setUp(self):
        create_data(self)

    def test_return_404_for_missing_resource(self):

        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('resource-detail', args=[666,]) # some non-existant pk
        response = admin_client.get(url)
        self.assertEqual(response.status_code,404) 

        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!') 
        url = reverse('resource-detail', args=[666,]) # some non-existant pk
        response = reg_client.get(url)
        self.assertEqual(response.status_code,404)

    def test_admin_user_can_query_own_resource(self):
        admin_user = get_user_model().objects.get(email='admin@admin.com')
        r = Resource.objects.filter(owner = admin_user)
        instance = r[0]
        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('resource-detail', args=[instance.pk,])
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_admin_user_can_query_others_resource(self):
        reg_user = get_user_model().objects.get(email='reguser@gmail.com')
        r = Resource.objects.filter(owner = reg_user)
        instance = r[0]
        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!')
        url = reverse('resource-detail', args=[instance.pk,])
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_regular_user_denied_access_to_others_resource(self):
        admin_user = get_user_model().objects.get(email='admin@admin.com')
        r = Resource.objects.filter(owner = admin_user)
        instance = r[0]
        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!') 
        url = reverse('resource-detail', args=[instance.pk,])
        response = reg_client.get(url)
        self.assertEqual(response.status_code,404)

    def test_regular_user_given_access_to_own_resource(self):
        reg_user = get_user_model().objects.get(email='reguser@gmail.com')
        r = Resource.objects.filter(owner = reg_user)
        instance = r[0]
        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!') 
        url = reverse('resource-detail', args=[instance.pk,])
        response = reg_client.get(url)
        self.assertEqual(response.status_code, 200)



'''
Tests for UserResourceList:
  - non-admin receives 403
  - using a pk that does not exist returns a 404
  - properly returns a list of Resources for a particular owner
'''
class UserResourceListTestCase(TestCase):
    def setUp(self):
        create_data(self)

    def test_404_from_nonexistent_user(self):

        # query all existing users, get the max pk, then add 1
        # to guarantee a non-existent user's pk
        all_users = get_user_model().objects.all()
        all_user_pks = [x.pk for x in all_users]
        max_pk = max(all_user_pks)
        nonexistent_user_pk = max_pk + 1

        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('user-resource-list', args=[nonexistent_user_pk,])
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_non_admin_user_gets_403_for_user_specific_list(self):
        '''
        regular users cannot access the /resources/user/<user pk>/ endpoint
        which lists the resources belonging to a specific user.  That
        functionality is already handled by a request to the /resources/ endpoint
        '''
        client = APIClient()
        client.login(email='reguser@gmail.com', password='abcd123!')

        # get the regular user's pk:
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk

        url = reverse('user-resource-list', args=[reguser_pk])
        response = client.get(url)
        self.assertEqual(response.status_code,403)

    def test_admin_user_correctly_can_get_user_specific_list(self):

        # establish the admin client:
        client = APIClient()
        client.login(email='admin@admin.com', password='abcd123!')

        # get the regular user's pk:
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk

        url = reverse('user-resource-list', args=[reguser_pk])
        response = client.get(url)
        data = response.data
        self.assertEqual(response.status_code,200) 
        self.assertEqual(len(response.data), 3)
        self.assertTrue(all([x.get('owner') == reguser_pk for x in data]))    

'''
Tests for listing Transfers:
  - lists all Transfers if requested by admin
  - If non-admin request, lists only those owned by that user
'''
class TransferListTestCase(TestCase):
    def setUp(self):
        create_data(self)

    def test_list_all_transfers_for_admin(self):
        '''
        This tests that the admin can list all existing Transfers
        ''' 
        t = Transfer.objects.all()
        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('transfer-list')
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 5) 

    def test_nonadmin_list_returns_only_owned_transfers(self):
        '''
        This tests that a regular user can only list the Transfer objects they originated.
        Note that this does NOT list the Transfers that happened for Resources they owned.
        
        ''' 
        reg_user = get_user_model().objects.get(email='reguser@gmail.com')
        user_transfers = Transfer.objects.user_transfers(reg_user)

        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!')
        url = reverse('transfer-list')
        response = reg_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

    def test_list_download_transfers_for_admin(self):
        '''
        This tests that the admin can list all the downloads, regardless of user
        '''
        t = Transfer.objects.all()
        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('transfer-list')
        url = '%s?download=true' % url
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

    def test_list_upload_transfers_for_admin(self):
        '''
        This tests that the admin can list all the uploads, regardless of user
        '''
        t = Transfer.objects.all()
        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('transfer-list')
        url = '%s?download=false' % url
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_list_download_transfers_for_reguser(self):
        '''
        This tests that the regular user can list all their downloads
        '''
        t = Transfer.objects.all()
        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!') 
        url = reverse('transfer-list')
        url = '%s?download=true' % url
        response = reg_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_list_upload_transfers_for_reguser(self):
        '''
        This tests that the regular user can list all their uploads
        Note that there were multiple uploads of this user's files.  
        However, only one of those was originated by this regular user; the
        other was transferred by an admin
        '''
        t = Transfer.objects.all()
        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!') 
        url = reverse('transfer-list')
        url = '%s?download=false' % url
        response = reg_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        
'''

Test for retrieving a specific Transfer:
  - returns 404 if the pk does not exist regardless of user
  - returns 404 if a non-admin user requests a Transfer
    owned by someone else
  - returns correctly if admin requests Transfer owned by someone else
  - returns correctly if admin requests Transfer owned by themself
'''
class TransferDetailTestCase(TestCase):
    def setUp(self):
        create_data(self)

    def test_return_404_for_missing_transfer(self):

        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('transfer-detail', args=[666,]) # some non-existant pk
        response = admin_client.get(url)
        self.assertEqual(response.status_code,404) 

        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!') 
        url = reverse('transfer-detail', args=[666,]) # some non-existant pk
        response = reg_client.get(url)
        self.assertEqual(response.status_code,404)

    def test_admin_user_can_query_own_transfer(self):
        admin_user = get_user_model().objects.get(email='admin@admin.com')
        t = Transfer.objects.user_transfers(admin_user)
        instance = t[0]
        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('transfer-detail', args=[instance.pk,])
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 200)

        # check that the Resource 'wrapped' by the Transfer is in fact
        # owned by the admin:
        data = response.data
        resource_pk = data['resource']
        r = Resource.objects.get(pk=resource_pk)
        owner = r.get_owner()
        self.assertEqual(owner, admin_user)

    def test_admin_user_can_query_others_transfer(self):
        # get an instance of a regular user's Transfer
        reg_user = get_user_model().objects.get(email='reguser@gmail.com')
        t = Transfer.objects.user_transfers(reg_user)
        instance = t[0]

        # create admin client:
        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('transfer-detail', args=[instance.pk,])
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 200)

        # check that the Resource 'wrapped' by the Transfer is in fact
        # owned by the other/regular user:
        data = response.data
        resource_pk = data['resource']
        r = Resource.objects.get(pk=resource_pk)
        owner = r.get_owner()
        self.assertEqual(owner, reg_user)

    def test_regular_user_can_query_own_transfer(self):
        # get an instance of a regular user's Transfer
        reg_user = get_user_model().objects.get(email='reguser@gmail.com')
        t = Transfer.objects.user_transfers(reg_user)
        instance = t[0]

        # create regular client:
        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!') 
        url = reverse('transfer-detail', args=[instance.pk,])
        response = reg_client.get(url)
        self.assertEqual(response.status_code, 200)

        # check that the Resource 'wrapped' by the Transfer is in fact
        # owned by the other/regular user:
        data = response.data
        resource_pk = data['resource']
        r = Resource.objects.get(pk=resource_pk)
        owner = r.get_owner()
        self.assertEqual(owner, reg_user) 

    def test_regular_user_cannot_query_others_transfer(self):
        # get an instance of another user's Transfer (here, the admins)
        admin_user = get_user_model().objects.get(email='admin@admin.com')
        t = Transfer.objects.user_transfers(admin_user)
        instance = t[0]

        # create regular client:
        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!') 
        url = reverse('transfer-detail', args=[instance.pk,])
        response = reg_client.get(url)
        self.assertEqual(response.status_code, 404)
      

'''
Tests for UserTransferList:
  - non-admin receives 403
  - using a pk (of a user) that does not exist returns a 404
  - properly returns a list of Transfers for a particular owner
'''
class UserTransferListTestCase(TestCase):
    def setUp(self):
        create_data(self)   

    def test_404_from_nonexistent_user_for_user_transfer_list(self):

        # query all existing users, get the max pk, then add 1
        # to guarantee a non-existent user's pk
        all_users = get_user_model().objects.all()
        all_user_pks = [x.pk for x in all_users]
        max_pk = max(all_user_pks)
        nonexistent_user_pk = max_pk + 1

        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('user-transfer-list', args=[nonexistent_user_pk,])
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_non_admin_user_gets_403_for_user_specific_transfer_list(self):
        '''
        regular users cannot access the /resources/user/<user pk>/ endpoint
        which lists the resources belonging to a specific user.  That
        functionality is already handled by a request to the /resources/ endpoint
        '''
        client = APIClient()
        client.login(email='reguser@gmail.com', password='abcd123!')

        # get the regular user's pk:
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk

        url = reverse('user-transfer-list', args=[reguser_pk])
        response = client.get(url)
        self.assertEqual(response.status_code,403)

    def test_admin_user_correctly_can_get_user_specific_transfer_list(self):

        # establish the admin client:
        client = APIClient()
        client.login(email='admin@admin.com', password='abcd123!')

        # get the regular user's pk:
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk

        url = reverse('user-transfer-list', args=[reguser_pk])
        response = client.get(url)
        data = response.data
        self.assertEqual(response.status_code,200) 
        self.assertEqual(len(response.data), 3)
        owner_status = []
        for item in data:
            resource_pk = item['resource']
            resource_obj = Resource.objects.get(pk=resource_pk)
            owner_status.append(resource_obj.owner == u)
        self.assertTrue(all(owner_status))

'''
Tests for listing Users:
  - admin users can list all users
  - admin users can list info about specific user
  - non-admin users do not have access to anything (returns 403)
'''
class UserListTestCase(TestCase):
    def setUp(self):
        create_data(self)

    def test_list_all_users_by_admin(self):
        # establish the admin client:
        client = APIClient()
        client.login(email='admin@admin.com', password='abcd123!')        

        url = reverse('user-list')
        response = client.get(url)
        data = response.data
        self.assertEqual(response.status_code,200) 
        self.assertEqual(len(response.data), 3)

    def test_list_specific_user_by_admin(self):
        # establish the admin client:
        client = APIClient()
        client.login(email='admin@admin.com', password='abcd123!')        

        # get the regular user's pk:
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk

        url = reverse('user-detail', args=[reguser_pk])
        response = client.get(url)
        data = response.data
        self.assertEqual(response.status_code,200) 
        self.assertEqual(data['email'], 'reguser@gmail.com')

    def test_regular_user_cannot_list_users(self):
        # establish a "regular" client:
        client = APIClient()
        client.login(email='reguser@gmail.com', password='abcd123!')        

        # check that querying all users is blocked:
        url = reverse('user-list')
        response = client.get(url)
        data = response.data
        self.assertEqual(response.status_code,403)

        # Now check that they cannot check even their own data:
        # get the regular user's pk:
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk

        url = reverse('user-detail', args=[reguser_pk])
        response = client.get(url)
        data = response.data
        self.assertEqual(response.status_code,403) 




'''
Tests for creating Users:
  - admin user can create a user with a specific username/email/pwd
  - non-admin users do not have access to anything (returns 403)
'''
class UserCreateTestCase(TestCase):
    def setUp(self):
        create_data(self)

    def test_admin_can_create_user(self):
        # establish the admin client:
        client = APIClient()
        client.login(email='admin@admin.com', password='abcd123!')

        # get the admin user's pk:
        u = get_user_model().objects.filter(email='admin@admin.com')[0]
        adminuser_pk = u.pk

        url = reverse('user-list')
        data = {'email':'reguser@email.com', \
                'password': 'abcd123!', \
        }
        response = client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)  

        u = get_user_model().objects.filter(email='reguser@email.com')
        self.assertEqual(len(u), 1)

    def test_regular_user_cannot_create_user(self):
        # establish the admin client:
        client = APIClient()
        client.login(email='reguser@gmail.com', password='abcd123!')

        # get the admin user's pk:
        u = get_user_model().objects.filter(email='admin@admin.com')[0]
        adminuser_pk = u.pk

        url = reverse('user-list')
        data = {'email':'anotherreguser@email.com', \
                'password': 'abcd123!', \
        }
        response = client.post(url, data, format='json')
        self.assertEqual(response.status_code, 403)  


'''
Tests for User deletion:
  - deletion of User causes deletion of all associated entities
  - non-admin cannot delete users
'''
class UserDeleteTestCase(TestCase):
    def setUp(self):
        create_data(self)

    def test_admin_can_delete_user(self):
        # establish the admin client:
        client = APIClient()
        client.login(email='admin@admin.com', password='abcd123!')

        u = get_user_model().objects.filter(email='reguser@gmail.com')
        self.assertEqual(len(u), 1)

        # get the reg user's pk:
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk

        url = reverse('user-detail', args=[reguser_pk,])
        response = client.delete(url)  
        u = get_user_model().objects.filter(email='reguser@gmail.com')
        self.assertEqual(len(u), 0)

    def test_admin_deletion_of_user_cascades(self):
        client = APIClient()
        client.login(email='admin@admin.com', password='abcd123!')

        # query for the user and ensure there are existing Resource/Transfer
        # instances associated with that user
        u = get_user_model().objects.filter(email='reguser@gmail.com')
        reguser = u[0]
        r = Resource.objects.user_resources(reguser)
        t = Transfer.objects.user_transfers(reguser)
        self.assertEqual(len(u), 1)
        self.assertEqual(len(r), 3)
        self.assertEqual(len(t), 3)

        # get the admin user's pk:
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk

        # delete the user and check that the associated items are ALSO deleted:
        url = reverse('user-detail', args=[reguser_pk,])
        response = client.delete(url)  
        u = get_user_model().objects.filter(email='reguser@gmail.com')
        r = Resource.objects.user_resources(reguser)
        t = Transfer.objects.user_transfers(reguser)
        self.assertEqual(len(u), 0)
        self.assertEqual(len(r), 0)
        self.assertEqual(len(t), 0)

    def test_reguser_cannot_delete_user(self):
        # establish the admin client:
        client = APIClient()
        client.login(email='reguser@gmail.com', password='abcd123!')

        u = get_user_model().objects.filter(email='otheruser@gmail.com')
        self.assertEqual(len(u), 1)
        otheruser_pk = u[0].pk

        url = reverse('user-detail', args=[otheruser_pk,])
        response = client.delete(url)  
        self.assertEqual(response.status_code, 403)

'''
Tests for batch list (TransferCoordinator):
  - lists all TransferCoordinators if requested by admin
  - If non-admin request, lists only TransferCoordinator objects owned by that user
'''
class TransferCoordinatorListTestCase(TestCase):
    def setUp(self):
        create_data(self)

    def test_list_all_transfercoordinators_for_admin(self):
        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('batch-list')
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4) 

    def test_nonadmin_list_returns_only_owned_transfers(self):
        reg_user = get_user_model().objects.get(email='reguser@gmail.com')
        user_tc = TransferCoordinator.objects.user_transfer_coordinators(reg_user)
        user_tc_pk = set([x.pk for x in user_tc]) # the primary keys of the 

        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!')
        url = reverse('batch-list')
        response = reg_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        data = response.data
        result_set = set()
        for item in data:
            result_set.add(item['id'])
        self.assertTrue(user_tc_pk == result_set)

    def test_unauthenticated_user_gets_403_for_transfercoordinator_list(self):
        client = APIClient()
        url = reverse('batch-list')
        response = client.get(url)
        self.assertEqual(response.status_code, 403)

'''
Tests for batch detail (TransferCoordinator):
  - returns 404 if the pk does not exist regardless of requesting user
  - returns 404 if a non-admin user requests a TransferCoordinator
    owned by someone else
  - returns correctly if admin requests TransferCoordinator owned by someone else
  - returns correctly if admin requests TransferCoordinator owned by themself
'''
class TransferCoordinatorDetailTestCase(TestCase):
    def setUp(self):
        create_data(self)

    def test_return_404_for_missing_tc(self):

        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('batch-detail', args=[666,]) # some non-existant pk
        response = admin_client.get(url)
        self.assertEqual(response.status_code,404) 

        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!') 
        url = reverse('batch-detail', args=[666,]) # some non-existant pk
        response = reg_client.get(url)
        self.assertEqual(response.status_code,404)

    def test_admin_user_can_query_own_tc(self):
        admin_user = get_user_model().objects.get(email='admin@admin.com')
        t = TransferCoordinator.objects.user_transfer_coordinators(admin_user)
        instance = t[0]
        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('batch-detail', args=[instance.pk,])
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 200)

        # check that the Resource 'wrapped' by the TransferCoordinator is in fact
        # owned by the admin:
        data = response.data
        tc_pk = data['id']
        transfers = Transfer.objects.filter(coordinator__pk = tc_pk)
        owners = list(set([t.resource.owner for t in transfers]))
        self.assertTrue(len(owners) == 1)
        self.assertTrue(owners[0] == admin_user)

    def test_admin_user_can_query_others_tc(self):
        # get an instance of a regular user's TransferCoordinator
        reg_user = get_user_model().objects.get(email='reguser@gmail.com')
        t = TransferCoordinator.objects.user_transfer_coordinators(reg_user)
        instance = t[0]

        # create admin client:
        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('batch-detail', args=[instance.pk,])
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 200)

        # check that the TransferCoordinator is in fact
        # owned by the regular user:
        data = response.data
        tc_pk = data['id']
        tc = TransferCoordinator.objects.get(pk=tc_pk)
        transfers_for_this_tc = Transfer.objects.filter(coordinator=tc)
        owners = list(set([x.resource.owner for x in transfers_for_this_tc]))
        self.assertEqual(len(owners), 1)
        self.assertEqual(owners[0], reg_user)

    def test_regular_user_can_query_own_tc(self):
        # get an instance of a regular user's TransferCoordinator
        reg_user = get_user_model().objects.get(email='reguser@gmail.com')
        t = TransferCoordinator.objects.user_transfer_coordinators(reg_user)
        instance = t[0]

        # create regular client:
        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!') 
        url = reverse('batch-detail', args=[instance.pk,])
        response = reg_client.get(url)
        self.assertEqual(response.status_code, 200)

        # check that the TransferCoordinator is in fact
        # owned by the other/regular user:
        data = response.data
        tc_pk = data['id']
        transfers = Transfer.objects.filter(coordinator__pk = tc_pk)
        owners = list(set([t.resource.owner for t in transfers]))
        self.assertTrue(len(owners) == 1)
        self.assertTrue(owners[0] == reg_user)

    def test_regular_user_cannot_query_others_tc(self):
        # get an instance of another user's TransferCoordinator (here, the admins)
        admin_user = get_user_model().objects.get(email='admin@admin.com')
        t = TransferCoordinator.objects.user_transfer_coordinators(admin_user)
        instance = t[0]

        # create regular client:
        reg_client = APIClient()
        reg_client.login(email='reguser@gmail.com', password='abcd123!') 
        url = reverse('batch-detail', args=[instance.pk,])
        response = reg_client.get(url)
        self.assertEqual(response.status_code, 404)

'''
Tests for UserBatchList (TransferCoordinator):
  - non-admin receives 403
  - using a pk that does not exist returns a 404
  - properly returns a list of TransferCoordinators for a particular owner
'''
class TransferCoordinatorUserListCase(TestCase):
    def setUp(self):
        create_data(self)

    def test_404_from_nonexistent_user_for_user_tc_list(self):

        # query all existing users, get the max pk, then add 1
        # to guarantee a non-existent user's pk
        all_users = get_user_model().objects.all()
        all_user_pks = [x.pk for x in all_users]
        max_pk = max(all_user_pks)
        nonexistent_user_pk = max_pk + 1

        admin_client = APIClient()
        admin_client.login(email='admin@admin.com', password='abcd123!') 
        url = reverse('user-batch-list', args=[nonexistent_user_pk,])
        response = admin_client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_non_admin_user_gets_403_for_user_specific_tc_list(self):
        '''
        regular users cannot access the /resources/user/<user pk>/ endpoint
        which lists the resources belonging to a specific user.  That
        functionality is already handled by a request to the /resources/ endpoint
        '''
        client = APIClient()
        client.login(email='reguser@gmail.com', password='abcd123!')

        # get the regular user's pk:
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk

        url = reverse('user-batch-list', args=[reguser_pk])
        response = client.get(url)
        self.assertEqual(response.status_code,403)

    def test_admin_user_correctly_can_get_user_specific_tc_list(self):

        # establish the admin client:
        client = APIClient()
        client.login(email='admin@admin.com', password='abcd123!')

        # get the regular user's pk:
        u = get_user_model().objects.filter(email='reguser@gmail.com')[0]
        reguser_pk = u.pk

        url = reverse('user-batch-list', args=[reguser_pk])
        response = client.get(url)
        data = response.data
        self.assertEqual(response.status_code, 200) 
        self.assertEqual(len(response.data), 2)

        # check that the TransferCoordinators returned are all properly owned by reg_user
        owner_list = []
        for item in data:
            tc_pk = item['id']
            transfers = Transfer.objects.filter(coordinator__pk = tc_pk)
            owners = [t.resource.owner for t in transfers]
            owner_list.extend(owners)
        owner_list = list(set(owner_list))
        self.assertTrue(len(owner_list) == 1)
        self.assertTrue(owner_list[0] == u)


'''
Tests for completion marking:
  - unauthenticated requests are rejected
  - marks the particular transfer complete
  - if not the final transfer, TransferCoordinator stays 'incomplete'
  - if it is the final transfer, TransferCoordinator marked complete
'''
class CompletionMarkingTestCase(TestCase):

    def setUp(self):
        self.regular_user = get_user_model().objects.create_user(email='reguser@gmail.com', password='abcd123!')

        # create a couple of resources owned by the regular user:
        r1 = Resource.objects.create(
            source='google_storage',
            path='gs://a/b/reg_owned1.txt',
            size=500,
            owner=self.regular_user,
        )
        r2 = Resource.objects.create(
            source='google_storage',
            path='gs://a/b/reg_owned2.txt',
            size=500,
            owner=self.regular_user,
        )

        tc1 = TransferCoordinator.objects.create()

        t1 = Transfer.objects.create(
            download=True,
            resource = r1,
            destination = 'dropbox',
            coordinator = tc1,
            originator = self.regular_user
        )
        t2 = Transfer.objects.create(
            download=True,
            resource = r2,
            destination = 'dropbox',
            coordinator = tc1,
            originator = self.regular_user
        )

    def test_single_worker_completion_signal(self):
        '''
        This tests where one of many workers has completed.  Not ALL 
        have completed, so the TransferCoordinator stays incomplete
        '''
        # query the database and get the TransferCoordinator and its Transfer instances:
        tc = TransferCoordinator.objects.get(pk=1)
        transfers = Transfer.objects.filter(coordinator = tc)

        d = {}
        token = settings.CONFIG_PARAMS['token']
        obj=DES.new(settings.CONFIG_PARAMS['enc_key'], DES.MODE_ECB)
        enc_token = obj.encrypt(token)
        b64_str = base64.encodestring(enc_token)
        d['token'] = b64_str
        d['transfer_pk'] = 1
        d['coordinator_pk'] = 1
        d['success'] = True

        client = APIClient()
        url = reverse('transfer-complete')
        response = client.post(url, d, format='json')
        self.assertEqual(response.status_code, 200)

        # query database to see that the Transfer was marked complete, but the
        # coordinator is still incomplete
        t = Transfer.objects.get(pk=1)
        self.assertTrue(t.completed)
        tc = TransferCoordinator.objects.get(pk=1)
        self.assertEqual(tc.completed, False)

    def test_full_completion_signal(self):
        '''
        This tests where both of two workers have completed.  ALL 
        have completed, so the TransferCoordinator becomes complete
        '''
        # query the database and get the TransferCoordinator and its Transfer instances:
        tc = TransferCoordinator.objects.get(pk=1)
        transfers = Transfer.objects.filter(coordinator = tc)

        token = settings.CONFIG_PARAMS['token']
        obj=DES.new(settings.CONFIG_PARAMS['enc_key'], DES.MODE_ECB)
        enc_token = obj.encrypt(token)
        b64_str = base64.encodestring(enc_token)

        d1 = {}
        d1['token'] = b64_str
        d1['transfer_pk'] = 1
        d1['coordinator_pk'] = 1
        d1['success'] = True

        d2 = {}
        d2['token'] = b64_str
        d2['transfer_pk'] = 2
        d2['coordinator_pk'] = 1
        d2['success'] = True

        client = APIClient()
        url = reverse('transfer-complete')
        response1 = client.post(url, d1, format='json')
        self.assertEqual(response1.status_code, 200)
        response2 = client.post(url, d2, format='json')
        self.assertEqual(response2.status_code, 200)

        # query database to see that the Transfer was marked complete, but the
        # coordinator is still incomplete
        t1 = Transfer.objects.get(pk=1)
        self.assertTrue(t1.completed)
        t2 = Transfer.objects.get(pk=2)
        self.assertTrue(t2.completed)
        tc = TransferCoordinator.objects.get(pk=1)
        self.assertTrue(tc.completed)

    def test_completion_signal_with_wrong_token_is_rejected(self):
        '''
        This tests where a bad token is sent.  Should reject with 404
        '''
        # query the database and get the TransferCoordinator and its Transfer instances:
        tc = TransferCoordinator.objects.get(pk=1)
        transfers = Transfer.objects.filter(coordinator = tc)

        bad_token = 'xxxxYYYY'
        obj=DES.new(settings.CONFIG_PARAMS['enc_key'], DES.MODE_ECB)
        enc_token = obj.encrypt(bad_token)
        bad_b64_str = base64.encodestring(enc_token)

        d1 = {}
        d1['token'] = bad_b64_str
        d1['transfer_pk'] = 1
        d1['coordinator_pk'] = 1
        d1['success'] = True

        client = APIClient()
        url = reverse('transfer-complete')
        response1 = client.post(url, d1, format='json')
        self.assertEqual(response1.status_code, 404)

    def test_incorrect_transfer_pk_on_completion(self):
        '''
        This tests where an incorrect pk is given for the transfer
        '''
        # query the database and get the TransferCoordinator and its Transfer instances:
        tc = TransferCoordinator.objects.get(pk=1)
        transfers = Transfer.objects.filter(coordinator = tc)

        d = {}
        token = settings.CONFIG_PARAMS['token']
        obj=DES.new(settings.CONFIG_PARAMS['enc_key'], DES.MODE_ECB)
        enc_token = obj.encrypt(token)
        b64_str = base64.encodestring(enc_token)
        d['token'] = b64_str
        d['transfer_pk'] = 100 # an invalid pk
        d['success'] = True

        client = APIClient()
        url = reverse('transfer-complete')
        response = client.post(url, d, format='json')
        self.assertEqual(response.status_code, 400)

    def test_bad_payload_on_completion(self):
        '''
        This tests where required info is missing in the request
        '''
        # query the database and get the TransferCoordinator and its Transfer instances:
        tc = TransferCoordinator.objects.get(pk=1)
        transfers = Transfer.objects.filter(coordinator = tc)

        d = {}
        token = settings.CONFIG_PARAMS['token']
        obj=DES.new(settings.CONFIG_PARAMS['enc_key'], DES.MODE_ECB)
        enc_token = obj.encrypt(token)
        b64_str = base64.encodestring(enc_token)
        d['token'] = b64_str
        # note: missing the transfer_pk key
        d['success'] = True

        client = APIClient()
        url = reverse('transfer-complete')
        response = client.post(url, d, format='json')
        self.assertEqual(response.status_code, 400)

















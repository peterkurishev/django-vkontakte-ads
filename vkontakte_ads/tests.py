# -*- coding: utf-8 -*-
from django.test import TestCase
from django.conf import settings
from django.core.files import File
from oauth_tokens.models import AccessToken
from models import Account, Campaign, Ad, Targeting, Client, Report, Stat, Budget, Layout, Statistic, Image, TargetingStats
from datetime import datetime, date
from mock import Mock
import simplejson as json

IMAGE_PATH = '/home/ramusus/test.jpg'
IMAGE_INITIAL_FIELDS = {'hash': '3620036d2588f91bc51829dd55754181', 'photo_hash': '32c9a0192c', 'photo': 'size:s|server:6167|owner_id:16982350|photo_hash:32c9a0192c|name:32c9a0192cx|width:90|height:65|kid:6e953128d1c79f28513aa976a69e92b8|hash:3620036d2588f91bc51829dd55754181', 'server': 6167}

ACCOUNT_ID = 1600019335
CAMPAIGN_ID = 1001099353
AD_ID = 3780349

ACCOUNT_ID2 = 1900000934
CLIENT_ID = 1600599323

class VkontakteAdsTest(TestCase):

    def setUp(self):
        self.objects_to_delete = []

    def tearDown(self):
        for object in self.objects_to_delete:
            object.delete()

    def test_fetch_accounts(self):

        self.assertEqual(Account.objects.count(), 0)
        Account.remote.fetch()
        count = Account.objects.count()
        self.assertTrue(count > 0)
        Account.remote.fetch()
        self.assertEqual(Account.objects.count(), count)

    def commentedtest_fetch_account_budget(self):
        '''
        Commented - only owner of account have permission to do API call
        '''
        account = Account.objects.create(remote_id=ACCOUNT_ID)

        self.assertEqual(Budget.objects.count(), 0)

        account.fetch_budget()
        self.assertEqual(Budget.objects.count(), 1)

        account.fetch_budget()
        self.assertEqual(Budget.objects.count(), 1)

    def test_fetch_clients(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID2)
        self.assertEqual(Client.objects.count(), 0)

        account.fetch_clients()
        count = Client.objects.count()
        self.assertNotEqual(count, 0)

        account.fetch_clients()
        self.assertEqual(Client.objects.count(), count)

    def test_fetch_campaigns(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        self.assertEqual(Campaign.objects.count(), 0)

        account.fetch_campaigns()
        campaigns_count = Campaign.objects.count()
        self.assertNotEqual(campaigns_count, 0)

        account.fetch_campaigns()
        self.assertEqual(Campaign.objects.count(), campaigns_count)

        # fetch only 2 campaings
        ids = [int(id) for id in Campaign.objects.values_list('remote_id', flat=True)[:1]]
        Campaign.objects.all().delete()
        self.assertEqual(Campaign.objects.count(), 0)
        account.fetch_campaigns(ids)
        self.assertEqual(Campaign.objects.count(), 1)

    def test_fetch_campaign_reports(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaign = Campaign.objects.create(remote_id=CAMPAIGN_ID, account=account, fetched=datetime.now())
        self.assertEqual(Report.objects.count(), 0)

        campaign.fetch_reports()
        reports_count = Report.objects.count()
        self.assertTrue(reports_count > 0)

        # test replacing old reports
        campaign.fetch_reports()
        self.assertEqual(Report.objects.count(), reports_count)

        # all time
        Report.objects.all().delete()
        campaign.fetch_reports(group_time=2)
        self.assertEqual(Report.objects.count(), 1)

        # by months
        Report.objects.all().delete()
        campaign.fetch_reports(group_time=1)
        reports_count = Report.objects.count()
        self.assertTrue(reports_count > 0)

        # test replacing old reports
        campaign.fetch_reports(group_time=1)
        self.assertEqual(Report.objects.count(), reports_count)

    def test_fetch_account_campaigns_reports(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaigns = account.fetch_campaigns()

        self.assertEqual(Report.objects.count(), 0)

        account.fetch_campaigns_reports()
        reports_count = Report.objects.count()
        self.assertTrue(reports_count > 0)
        self.assertEqual(reports_count, len(campaigns))

        account.fetch_campaigns_reports()
        self.assertEqual(Report.objects.count(), reports_count)

    def test_fetch_campaign_statisics(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaign = Campaign.objects.create(remote_id=CAMPAIGN_ID, account=account, fetched=datetime.now())
        self.assertEqual(Statistic.objects.count(), 0)

        start_time = datetime.now()
        campaign.fetch_statistics()
        self.assertEqual(Statistic.objects.count(), 1)

        stat = Statistic.objects.all()[0]
        self.assertEqual(stat.content_object, campaign)
        self.assertEqual(stat.overall, True)

        self.assertTrue(stat.fetched > start_time)
        fetched_time = stat.fetched

        campaign.fetch_statistics()
        self.assertEqual(Statistic.objects.count(), 1)

        stat = Statistic.objects.all()[0]
        self.assertTrue(stat.fetched > fetched_time)

        campaign.fetch_statistics(period='month')
        self.assertTrue(Statistic.objects.count() > 1)

    def test_fetch_campaign_stats(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaign = Campaign.objects.create(remote_id=CAMPAIGN_ID, account=account, fetched=datetime.now())
        self.assertEqual(Stat.objects.count(), 0)

        campaign.fetch_stats()
        instances_count = Stat.objects.count()
        self.assertEqual(instances_count, 1)

        stat = Stat.objects.all()[0]
        self.assertEqual(stat.campaign, campaign)
        self.assertEqual(stat.data, {'id': stat.campaign.remote_id, 'type': 1})

        campaign.fetch_stats()
        self.assertEqual(Stat.objects.count(), 2)

    def test_fetch_campaign_ads_stats(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaign = Campaign.objects.create(remote_id=CAMPAIGN_ID, account=account, fetched=datetime.now())
        campaign.fetch_ads()
        self.assertEqual(Stat.objects.count(), 0)

        campaign.fetch_ads_stats()
        instances_count = Stat.objects.count()
        self.assertEqual(instances_count, Ad.objects.count())

        for stat in Stat.objects.all():
            self.assertEqual(stat.data, {'type': 0, 'id': int(stat.ad.remote_id)})

    def test_fetch_ad_stats(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaign = Campaign.objects.create(remote_id=CAMPAIGN_ID, account=account, fetched=datetime.now())
        campaign.fetch_ads()
        ad = Ad.objects.all()[0]
        self.assertEqual(Stat.objects.count(), 0)

        ad.fetch_stats()
        instances_count = Stat.objects.count()
        self.assertTrue(instances_count > 0)

        stat = Stat.objects.all()[0]
        self.assertEqual(stat.ad, ad)
        self.assertEqual(stat.data, {'id': stat.ad.remote_id, 'type': 0})

        ad.fetch_stats()
        self.assertEqual(Stat.objects.count(), instances_count*2)

    def test_refresh_ad(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaign = Campaign.objects.create(remote_id=CAMPAIGN_ID, account=account, fetched=datetime.now())
        campaign.fetch_ads()
        ad = campaign.ads.all()[0]
        cost = ad.cost_type
        ad.name = ad.name + '###'
        ad.save(commit_remote=False)
        ad.refresh()

        self.assertTrue('#' not in ad.name)
        self.assertEqual(ad.cost_type, cost)
        self.assertEqual(ad.campaign, campaign)
        self.assertEqual(ad.account, account)
        self.assertNotEqual(ad.fetched, None)

        ad = Ad.objects.get(id=ad.id)
        self.assertTrue('#' not in ad.name)

    def test_fetch_ads(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaign = Campaign.objects.create(remote_id=CAMPAIGN_ID, account=account, fetched=datetime.now())
        self.assertEqual(Ad.objects.count(), 0)

        campaign.fetch_ads()
        ads_count = Ad.objects.count()
        self.assertNotEqual(ads_count, 0)

        campaign.fetch_ads()
        self.assertEqual(Ad.objects.count(), ads_count)

        # fetch only 2 campaings
        ids = [int(id) for id in Ad.objects.values_list('remote_id', flat=True)[:1]]
        Ad.objects.all().delete()
        self.assertEqual(Ad.objects.count(), 0)
        campaign.fetch_ads(ids)
        self.assertEqual(Ad.objects.count(), 1)

    def test_fetch_cities_for_ad(self):

        if 'vkontakte_places' in settings.INSTALLED_APPS:
            from vkontakte_places.models import City

            account = Account.objects.create(remote_id=ACCOUNT_ID)
            campaign = Campaign.objects.create(remote_id=CAMPAIGN_ID, account=account, fetched=datetime.now())
            self.assertEqual(Targeting.objects.count(), 0)
            self.assertEqual(City.objects.count(), 0)

            campaign.fetch_ads_targeting([AD_ID])
            self.assertEqual(Targeting.objects.count(), 1)
            self.assertTrue(len(Targeting.objects.all()[0].cities.split(',')), 2)
            self.assertEqual(City.objects.count(), 2) # TODO: fix it

    def test_fetch_ads_targeting(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaign = Campaign.objects.create(remote_id=CAMPAIGN_ID, account=account, fetched=datetime.now())
        self.assertEqual(Targeting.objects.count(), 0)

        campaign.fetch_ads_targeting()
        ads_count = Targeting.objects.count()
        self.assertNotEqual(ads_count, 0)

        campaign.fetch_ads_targeting()
        self.assertEqual(Targeting.objects.count(), ads_count)

        # fetch only 2 campaings
        ids = [int(id) for id in Targeting.objects.values_list('remote_id', flat=True)[:1]]
        Targeting.objects.all().delete()
        self.assertEqual(Targeting.objects.count(), 0)
        campaign.fetch_ads_targeting(ids)
        self.assertEqual(Targeting.objects.count(), 1)

    def test_fetch_ads_layout(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaign = Campaign.objects.create(remote_id=CAMPAIGN_ID, account=account, fetched=datetime.now())
        self.assertEqual(Layout.objects.count(), 0)

        campaign.fetch_ads_layout()
        ads_count = Layout.objects.count()
        self.assertNotEqual(ads_count, 0)

        campaign.fetch_ads_layout()
        self.assertEqual(Layout.objects.count(), ads_count)

        # fetch only 2 campaings
        ids = [int(id) for id in Layout.objects.values_list('remote_id', flat=True)[:1]]
        Layout.objects.all().delete()
        self.assertEqual(Layout.objects.count(), 0)
        campaign.fetch_ads_layout(ids)
        self.assertEqual(Layout.objects.count(), 1)

    def test_parse_account(self):

        response = '''
            {"response":[{"account_id":"1600001217","account_status":1,"access_role":"admin"}]}
            '''
        instance = Account()
        instance.parse(json.loads(response)['response'][0])
        instance.save()

        self.assertEqual(instance.remote_id, 1600001217)
        self.assertEqual(instance.account_status, True)
        self.assertEqual(instance.access_role, 'admin')

        instance.delete()
        response = '''
            {"response":[{"account_id":"1600001217","account_status":0,"access_role":"admin"}]}
            '''
        instance = Account()
        instance.parse(json.loads(response)['response'][0])
        instance.save()

        self.assertEqual(instance.account_status, False)

    def test_parse_client(self):

        response = '''
            {"response":[{"id":"107111","name":"Ford","day_limit":170,"all_limit":3000}]}
            '''
        account = Account.objects.create(remote_id=1)
        instance = Client(account=account, fetched=datetime.now())
        instance.parse(json.loads(response)['response'][0])
        instance.save()

        self.assertEqual(instance.account, account)
        self.assertEqual(instance.remote_id, 107111)
        self.assertEqual(instance.name, 'Ford')
        self.assertEqual(instance.day_limit, 170)
        self.assertEqual(instance.all_limit, 3000)

    def test_parse_campaign(self):

        response = '''
            {"response":[
                {"id":"111","name":"Campaign1","status":0,"day_limit":2000,"all_limit":1000000,"start_time":"0","stop_time":"0"},
                {"id":"222","name":"Campaign2","status":1,"day_limit":6000,"all_limit":9000000,"start_time":"1298365200","stop_time":"1298451600"}
            ]}
            '''
        account = Account.objects.create(remote_id=1)
        instance = Campaign(account=account, fetched=datetime.now())
        instance.parse(json.loads(response)['response'][0])
        instance.save()

        self.assertEqual(instance.remote_id, 111)
        self.assertEqual(instance.name, "Campaign1")
        self.assertEqual(instance.status, False)
        self.assertEqual(instance.day_limit, 2000)
        self.assertEqual(instance.all_limit, 1000000)
        self.assertEqual(instance.start_time, None)
        self.assertEqual(instance.stop_time, None)

        instance = Campaign(account=account, fetched=datetime.now())
        instance.parse(json.loads(response)['response'][1])
        instance.save()

        self.assertTrue(isinstance(instance.account, Account))
        self.assertEqual(instance.account.remote_id, 1)

        self.assertEqual(instance.remote_id, 222)
        self.assertEqual(instance.name, "Campaign2")
        self.assertEqual(instance.status, True)
        self.assertEqual(instance.day_limit, 6000)
        self.assertEqual(instance.all_limit, 9000000)
        self.assertEqual(instance.start_time, datetime(2011,2,22,12,0,0))
        self.assertEqual(instance.stop_time, datetime(2011,2,23,12,0,0))

    def test_parse_ad(self):

        response = '''
            {"response":[
                {"id":"607256","campaign_id":"123","name":"Ad1","status":0,"approved":0,"all_limit":0,"cost_type":0,"cpm":118},
                {"id":"664868","campaign_id":"123","name":"Ad2","status":1,"approved":1,"all_limit":100,"cost_type":1,"cpc":488}
            ]}
            '''
        account = Account.objects.create(remote_id=1)
        campaign = Campaign.objects.create(account=account, remote_id=1, fetched=datetime.now())
        instance = Ad(campaign=campaign, fetched=datetime.now())
        instance.parse(json.loads(response)['response'][0])
        instance.save()

        self.assertTrue(isinstance(instance.campaign, Campaign))
        self.assertEqual(instance.campaign.remote_id, 1)

        self.assertEqual(instance.remote_id, 607256)
        self.assertEqual(instance.name, "Ad1")
        self.assertEqual(instance.status, False)
        self.assertEqual(instance.approved, False)
        self.assertEqual(instance.all_limit, 0)
        self.assertEqual(instance.cpm, 118)

        instance = Ad(campaign=campaign, fetched=datetime.now())
        instance.parse(json.loads(response)['response'][1])
        instance.save()

        self.assertEqual(instance.remote_id, 664868)
        self.assertEqual(instance.name, "Ad2")
        self.assertEqual(instance.status, True)
        self.assertEqual(instance.approved, True)
        self.assertEqual(instance.all_limit, 100)
        self.assertEqual(instance.cpc, 488)

    def test_parse_layout(self):

        response = '''
            {"response":[
                {"id":"111","campaign_id":"123","title":"Title","description":"Description","link_url":"http://vkontakte.ru","link_domain":"vkontakte.ru","preview_link":"http://vkontakte.ru/ads.php?act=preview_ad&mid=83813&id=111&t=1298281862&hash=71964c09f15a0f44bf"}
            ]}
            '''
        account = Account.objects.create(remote_id=1)
        campaign = Campaign.objects.create(account=account, remote_id=123, fetched=datetime.now())
        ad = Ad.objects.create(campaign=campaign, remote_id=111, cost_type=0, cpc=100, fetched=datetime.now())
        instance = ad.layout
        instance.parse(json.loads(response)['response'][0])
        instance.save()
        ad = Ad.objects.get(id=ad.id)

        self.assertEqual(ad.layout, instance)

        self.assertTrue(isinstance(instance.campaign, Campaign))
        self.assertEqual(instance.campaign.remote_id, 123)

        self.assertEqual(instance.remote_id, 111)
        self.assertEqual(instance.title, "Title")
        self.assertEqual(instance.description, "Description")

        self.assertEqual(instance.link_url, "http://vkontakte.ru")
        self.assertEqual(instance.link_domain, "vkontakte.ru")
        self.assertEqual(instance.preview_link, "http://vkontakte.ru/ads.php?act=preview_ad&mid=83813&id=111&t=1298281862&hash=71964c09f15a0f44bf")

    def test_parse_targeting(self):

        response = '''
            {"response":[{"id":"664868","campaign_id":"123","sex":"0","age_from":"0","age_to":"0","country":"1","cities":"2","count":"523","group_types":"","groups":"","interests":"232116,369651","districts":"125,126","stations":"","streets":"","schools":"1","positions":"","religions":"","statuses":"2,5","school_from":"0","school_to":"2010","uni_from":"0","uni_to":"2013","operators":"","tags":"SPbSU, Programming"}]}
            '''
        account = Account.objects.create(remote_id=1)
        campaign = Campaign.objects.create(account=account, remote_id=123, fetched=datetime.now())
        ad = Ad.objects.create(campaign=campaign, remote_id=664868, cost_type=0, cpc=100, fetched=datetime.now())
        instance = ad.targeting
        instance.parse(json.loads(response)['response'][0])
        instance.save()
        ad = Ad.objects.get(id=ad.id)

        self.assertEqual(ad.targeting, instance)

        self.assertTrue(isinstance(instance.campaign, Campaign))
        self.assertEqual(instance.campaign.remote_id, 123)

        self.assertEqual(instance.remote_id, 664868)
        self.assertEqual(instance.sex, 0)
        self.assertEqual(instance.age_from, 0)
        self.assertEqual(instance.age_to, 0)
        self.assertEqual(instance.country, 1)
        self.assertEqual(instance.cities, "2")
        self.assertEqual(instance.count, 523)
        self.assertEqual(instance.group_types, "")
        self.assertEqual(instance.groups, "")
        self.assertEqual(instance.interests, "232116,369651")
        self.assertEqual(instance.districts, "125,126")
        self.assertEqual(instance.stations, "")
        self.assertEqual(instance.streets, "")
        self.assertEqual(instance.schools, "1")
        self.assertEqual(instance.positions, "")
        self.assertEqual(instance.religions, "")
        self.assertEqual(instance.statuses, "2,5")
        self.assertEqual(instance.school_from, 0)
        self.assertEqual(instance.school_to, 2010)
        self.assertEqual(instance.uni_from, 0)
        self.assertEqual(instance.uni_to, 2013)
        self.assertEqual(instance.operators, "")
        self.assertEqual(instance.tags, "SPbSU, Programming")

    def test_parse_report(self):

        response = '''
            {"response":[
                {"clicks":"103","money":"1000.00","day":"2010-10-08","campaign_id":123,"client_id":123,"client_name":"Ford","campaign_name":"Campaign1","ctr":"0.199","impressions":"51635"}
            ]}
            '''
        account = Account.objects.create(remote_id=1)
        Campaign.objects.create(account=account, remote_id=123, fetched=datetime.now())
        Client.objects.create(account=account, remote_id=123, fetched=datetime.now())

        instance = Report(time_from=datetime.now(), time_to=datetime.now())
        instance.parse(json.loads(response)['response'][0])
        instance.save()

        self.assertTrue(isinstance(instance.campaign, Campaign))
        self.assertEqual(instance.campaign.remote_id, 123)

        self.assertTrue(isinstance(instance.client, Client))
        self.assertEqual(instance.client.remote_id, 123)

        self.assertEqual(instance.clicks, 103)
        self.assertEqual(instance.impressions, 51635)
        self.assertEqual(instance.day, date(2010,10,8))
        self.assertEqual(instance.client_name, "Ford")
        self.assertEqual(instance.campaign_name, "Campaign1")
        self.assertEqual(instance.money, '1000.00')
        self.assertEqual(instance.ctr, '0.199')

#    def test_parse_statistics(self):
#
#        response = '''
#            {"response":[
#                {"id":123456,"type":"ad","stats":[
#                    {"day":"2012-03-17","spent":"7.57","impressions":3779,"clicks":3},
#                    {"day":"2012-03-18","spent":"20.47","impressions":8748,"clicks":13,"join_rate":3},
#                    {"day":"2012-03-19","spent":"6.47","impressions":2598,"clicks":5,"join_rate":1},
#                    {"day":"2012-03-20","spent":"3.67","impressions":1476,"clicks":1,"join_rate":1},
#                    {"day":"2012-03-21","spent":"1.43","impressions":515}
#                ]},
#                {"id":111222,"type":"ad","stats":[
#                    {"day":"2012-03-17","spent":"3.92","impressions":3272,"clicks":3,"join_rate":1},
#                    {"day":"2012-03-18","spent":"68.05","impressions":28139,"clicks":30,"join_rate":2},
#                    {"day":"2012-03-19","spent":"26.95","impressions":10768,"clicks":8,"join_rate":1},
#                    {"day":"2012-03-21","spent":"2.50","impressions":1012,"clicks":2}
#                ]}
#            ]}
#            '''
#        account = Account.objects.create(remote_id=1)
#
#        instance = Stat(account=account, period=0, data={})
#        instance.parse(json.loads(response)['response'][0][1])
#        instance.save()
#
#        self.assertEqual(instance.clicks, 789)
#        self.assertEqual(instance.impressions, 123456)
#        self.assertEqual(instance.month, '2011-03')
#        self.assertEqual(instance.money, '123.45')

    def test_parse_stat(self):

        response = '''
            {"response":[[
                {"month":"2011-02","impressions":0,"clicks":0,"money":"0.00"},
                {"month":"2011-03","impressions":123456,"clicks":789,"money":"123.45"}
            ]]}
            '''
        account = Account.objects.create(remote_id=1)

        instance = Stat(account=account, period=0, data={})
        instance.parse(json.loads(response)['response'][0][1])
        instance.save()

        self.assertEqual(instance.clicks, 789)
        self.assertEqual(instance.impressions, 123456)
        self.assertEqual(instance.month, '2011-03')
        self.assertEqual(instance.money, '123.45')

    def test_updating_tokens(self):

        final_tokens = 2 if getattr(settings, 'OAUTH_TOKENS_HISTORY', False) else 1

        AccessToken.objects.create(provider='vkontakte', expires=datetime.now(), access_token='4344810a0c67bb8a4361152d5a4348ab19443634361952d11bda2cdc7a42db6')
        self.assertEqual(AccessToken.objects.count(), 1)

        Account.remote.fetch()
        token = AccessToken.objects.latest()
        self.assertEqual(AccessToken.objects.count(), final_tokens)
        self.assertTrue(Account.objects.count() > 0)

        Account.remote.fetch()
        self.assertEqual(AccessToken.objects.count(), final_tokens)
        self.assertTrue(Account.objects.count() > 0)

        self.assertEqual(AccessToken.objects.latest(), token)

    def test_update_campaign(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        account.fetch_campaigns(ids=[CAMPAIGN_ID])
        self.assertEqual(Campaign.objects.count(), 1)

        campaign = Campaign.objects.all()[0]
        old_name = campaign.name
        campaign.name += u' _'
        campaign.save()

        # refresh data
        account.fetch_campaigns(ids=[CAMPAIGN_ID])
        campaign = Campaign.objects.all()[0]
        self.assertNotEqual(campaign.name, old_name)
        self.assertEqual(campaign.name, old_name + ' _')

        campaign.name = old_name
        campaign.save()

#    def test_update_client(self):
#
#        account = Account.objects.create(remote_id=ACCOUNT_ID2)
#        account.fetch_clients()
#
#        client = Client.objects.get(remote_id=CLIENT_ID)
#        old_name = client.name
#        client.name += u' _'
#        client.save()
#
#        # refresh data
#        account.fetch_clients()
#        client = Client.objects.get(remote_id=CLIENT_ID)
#        self.assertNotEqual(client.name, old_name)
#        self.assertEqual(client.name, old_name + ' _')
#
#        client.name = old_name
#        client.save()
#
#    def test_crud_client(self):
#
#        account = Account.objects.create(remote_id=ACCOUNT_ID2)
#        client = Client.remote.create(account=account, name='Test_client1', day_limit=1000, all_limit=2000)
#        self.objects_to_delete += [client]
#
#        self.assertTrue(client.remote_id > 0)
#        self.assertEqual(client.day_limit, 1000)
#        self.assertEqual(client.all_limit, 2000)
#        client.name = 'Test_client2'
#        client.save()
#
#        account.fetch_clients()
#        client1 = Client.objects.get(remote_id=client.remote_id)
#        self.assertEqual(client1.name, client.name) #fix deleting clients
#        self.assertEqual(client1.day_limit, 1000)
#        self.assertEqual(client1.all_limit, 2000)
#
#        client1.delete()
#        self.assertEqual(Client.objects.filter(remote_id=client.remote_id).count(), 0)
#
#        account.fetch_clients()
#        self.assertEqual(Client.objects.filter(remote_id=client.remote_id).count(), 0) #fix deleting clients
#        self.objects_to_delete = []

    def test_crud_campaign(self):

        # create
        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaign = Campaign.remote.create(account=account, name='Test_campaign1', day_limit=1000, all_limit=2000)
        self.objects_to_delete += [campaign]

        self.assertTrue(campaign.remote_id > 0)
        self.assertEqual(campaign.day_limit, 1000)
        self.assertEqual(campaign.all_limit, 2000)

        # update
        campaign.name = 'Test_campaign2'
        campaign.save()
        account.fetch_campaigns(ids=[campaign.remote_id])
        campaign1 = Campaign.objects.get(remote_id=campaign.remote_id)

        self.assertEqual(campaign1.name, campaign.name)
        self.assertEqual(campaign1.day_limit, 1000)
        self.assertEqual(campaign1.all_limit, 2000)

        # delete
        campaign1.delete()
        self.assertEqual(Campaign.objects.filter(remote_id=campaign.remote_id).count(), 0)
        account.fetch_campaigns(ids=[campaign.remote_id])
        self.assertEqual(Campaign.objects.filter(remote_id=campaign.remote_id).count(), 0)
        self.objects_to_delete = []

    def test_crud_ad(self):

        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaign = Campaign.remote.create(account=account, name='Test_campaign1', day_limit=1000, all_limit=2000)
        image = Image(**IMAGE_INITIAL_FIELDS)
        self.objects_to_delete += [campaign]

        self.assertTrue(campaign.remote_id > 0)

        # create
        ad = Ad(campaign=campaign, name='Test_ad1', status=False, cost_type=0, image=image, cpc=100,
            layout__title='111', layout__link_url='http://ya.ru', layout__description='q'*50)
        ad.save()
        self.objects_to_delete += [ad]

        # create another
        ad = Ad.remote.create(campaign=campaign, name='Test_ad2', status=False, cost_type=0, image=image, cpc=100,
            layout__title='111', layout__link_url='http://ya.ru', layout__description='q'*50)
        self.objects_to_delete += [ad]

        self.assertTrue(ad.remote_id > 0)
        self.assertEqual(ad.name, 'Test_ad2')
        self.assertEqual(ad.status, False)
        self.assertEqual(ad.cost_type, 0)
        self.assertEqual(ad.cpc, 100)

        # update
        ad.name = 'Test_ad3'
        ad.save()
        campaign.fetch_ads(ids=[ad.remote_id])
        ad1 = Ad.objects.get(remote_id=ad.remote_id)

        self.assertTrue(ad1.name == ad.name == 'Test_ad3')
        self.assertEqual(ad1.cpc, 100)

        # delete
        ad1.delete()
        self.assertEqual(Ad.objects.filter(remote_id=ad.remote_id).count(), 0)
        campaign.fetch_ads(ids=[ad.remote_id])
        self.assertEqual(Ad.objects.filter(remote_id=ad.remote_id).count(), 0)

        campaign.delete()
        self.objects_to_delete = []

    def test_upload_ad_image(self):

        image = Image(file=File(open(IMAGE_PATH)))
        ad = Ad(cost_type=0, cpc=100, image=image, campaign=Campaign(account=Account(remote_id=1), remote_id=1))
        url = ad.image.get_post_url()
        self.assertTrue('vkontakte.ru/upload.php?' in url)

        ad.image.upload()
        self.assertTrue(len(ad.image.hash) > 0)
        self.assertTrue(ad.image.width > 0)
        self.assertTrue(ad.image.height > 0)

    def test_update_fields(self):
        '''
        Test for generating update request with only changed fields
        '''
        Campaign.remote.api_call = Mock()
        Campaign.remote.api_call.return_value = [{'id': 1}]
        Ad.remote.api_call = Mock()
        Ad.remote.api_call.return_value = [{'id': 1}]

        # campaign
        account = Account.objects.create(remote_id=ACCOUNT_ID)
        campaign = Campaign.remote.create(account=account, name='Test_campaign1', day_limit=1000, all_limit=2000)
        Campaign.remote.api_call.assert_called_with(data=[{'status': 0, 'all_limit': 2000, 'name': 'Test_campaign1', 'day_limit': 1000}], account_id=ACCOUNT_ID, method='create')

        campaign.name = 'Test_campaign2'
        campaign.save()
        Campaign.remote.api_call.assert_called_with(data=[{'name': 'Test_campaign2', 'campaign_id': 1}], account_id=ACCOUNT_ID, method='update')

        # ad
        ad = Ad.remote.create(campaign=campaign, name='Test_ad1', status=False, cost_type=0, image=Image(), cpc=100)
        Ad.remote.api_call.assert_called_with(data=[{'status': 0, 'school_from': 0, 'hash': '', 'photo_hash': '', 'title': '', 'photo': '', 'link_url': '', 'cpc': 1.0, 'campaign_id': 1, 'server': None, 'cost_type': 0, 'age_to': 0, 'travellers': 0, 'country': 0, 'age_from': 0, 'sex': 0, 'uni_to': 0, 'school_to': 0, 'uni_from': 0, 'name': 'Test_ad1'}], account_id=ACCOUNT_ID, method='create')

        ad.name = 'Test_ad2'
        ad.save()
        Ad.remote.api_call.assert_called_with(data=[{'name': 'Test_ad2', 'ad_id': 1}], account_id=ACCOUNT_ID, method='update')

    def test_targeting_stats(self):

        stat = TargetingStats.remote.get(ad=Ad(account=Account.objects.create(remote_id=ACCOUNT_ID),
            layout__link_domain='www.ford.com',
            layout__link_url='http://www.ford.com/trucks/ranger/',
            targeting__sex=2,
            targeting__age_from=20,
            targeting__age_to=30))

        self.assertTrue(stat.audience_count > 0)
        self.assertTrue(stat.recommended_cpc > 0)
        self.assertTrue(stat.recommended_cpm > 0)
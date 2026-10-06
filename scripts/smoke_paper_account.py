"""Dedicated QA account smoke test. Credentials stay in ignored local data/."""
import json
import secrets
from pathlib import Path
from uuid import uuid4
import httpx
from dotenv import dotenv_values

def main():
    env=dotenv_values('.env');base=env['SUPABASE_URL'].rstrip('/');key=env['SUPABASE_SERVICE_ROLE_KEY']
    folder=Path('data/qa');folder.mkdir(parents=True,exist_ok=True);target=folder/'paper-account.json'
    with httpx.Client(timeout=45) as client:
        if target.exists():credentials=json.loads(target.read_text())
        else:
            credentials={'email':'dhanvest-qa-'+uuid4().hex+'@example.test','password':secrets.token_urlsafe(32)}
            response=client.post(base+'/auth/v1/admin/users',headers={'apikey':key,'Authorization':'Bearer '+key},
                json={**credentials,'email_confirm':True,'user_metadata':{'dhanvest_qa':True}})
            if response.status_code>=400:
                print('QA account creation failed; HTTP',response.status_code);return
            # Only this newly created QA user is recorded. No existing users or settings touched.
            credentials['user_id']=response.json()['id']
            with target.open('x') as output:json.dump(credentials,output)
        site='https://dhanvest.covers.bd'
        login=client.post(site+'/api/account/login',json={k:credentials[k] for k in ('email','password')})
        print('Dedicated QA sign-in:',login.status_code)
        if login.status_code!=200 or not login.json().get('access_token'):return
        token=login.json()['access_token'];headers={'Authorization':'Bearer '+token}
        first=client.get(site+'/api/paper/portfolio',headers=headers)
        print('Authenticated portfolio:',first.status_code)
        if first.status_code!=200:return
        data=first.json()
        assert data['account']['user_id']==credentials['user_id']
        assert data['account']['initial_cash']==1000000
        assert not data['positions'] and not data['trades']
        assert data['account']['cash']==1000000
        second=client.get(site+'/api/paper/portfolio',headers=headers)
        assert second.json()['account']['cash']==1000000
        anonymous=client.get(site+'/api/paper/portfolio')
        assert anonymous.status_code==401
        print('PASS: own-account isolation, initial BDT 1m, repeat opening preserves cash, anonymous access rejected.')
        print('No real/virtual trades submitted. Email delivery not tested; QA confirmation bypass is limited to this synthetic account.')

if __name__=='__main__':main()

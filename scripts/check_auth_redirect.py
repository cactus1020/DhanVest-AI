"""Check a dedicated QA auth link without sending mail or exposing tokens."""
import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import httpx
from dotenv import dotenv_values

EXPECTED = 'https://dhanvest.covers.bd/v2/practice'

def main():
    config = dotenv_values('.env')
    qa = json.loads(Path('data/qa/paper-account.json').read_text(encoding='utf-8'))
    base = config['SUPABASE_URL'].rstrip('/')
    key = config['SUPABASE_SERVICE_ROLE_KEY']
    try:
        with httpx.Client(timeout=httpx.Timeout(20,connect=5), follow_redirects=False) as client:
            # Generating a link does not send an email. Use the existing QA user only.
            generated = client.post(base+'/auth/v1/admin/generate_link',
                headers={'apikey':key,'Authorization':'Bearer '+key},
                json={'type':'magiclink','email':qa['email']})
            if generated.status_code != 200:
                raise SystemExit('QA link generation failed; HTTP '+str(generated.status_code))
            data = generated.json()
            properties = data.get('properties',data)
            link = properties['action_link']
            parsed = urlparse(link)
            if parsed.hostname != urlparse(base).hostname:
                raise SystemExit('Unexpected auth-link host; link was not opened.')
            redirect = parse_qs(parsed.query).get('redirect_to',[''])[0]
            assert redirect == EXPECTED, 'Auth default redirect does not match production.'
            print('Generated QA link redirect:',redirect)
            verified = client.get(link)
            location = urlparse(verified.headers.get('location',''))
            assert verified.status_code in (302,303), 'Auth verification did not return a redirect.'
            assert location.scheme+'://'+location.netloc+location.path == EXPECTED, 'Auth redirect did not reach the production route.'
            params = parse_qs(location.fragment)
            assert 'error' not in params, 'QA auth link failed verification.'
            token = params.get('access_token',[''])[0]
            assert token, 'Auth verification did not return a session.'
            portfolio = client.get('https://dhanvest.covers.bd/api/paper/portfolio',headers={'Authorization':'Bearer '+token})
            assert portfolio.status_code == 200, 'Live portfolio did not accept verified QA session.'
            assert portfolio.json()['account']['user_id'] == qa['user_id'], 'QA session owner mismatch.'
            print('PASS: live auth redirects to production and its verified session opens the existing QA portfolio.')
            print('No email sent; no new account, password change or trade. Mailbox delivery itself was not tested.')
    except httpx.HTTPError as error:
        raise SystemExit('Auth check network failure: '+type(error).__name__) from None

if __name__ == '__main__':main()

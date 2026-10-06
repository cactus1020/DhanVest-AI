"""Authenticated virtual-money trading. Never sends an order to an exchange."""
import os
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field


def auth_request(path, body=None, token=None):
    base = os.getenv('SUPABASE_URL', '').rstrip('/')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    if not base.startswith('https://') or not key:
        raise HTTPException(503, 'Account service is unavailable.')
    try:
        with httpx.Client(timeout=12) as client:
            response = client.request('GET' if token else 'POST', base+'/auth/v1/'+path,
                headers={'apikey':key, 'Authorization':'Bearer '+(token or key)}, json=body)
        if response.status_code >= 400:
            raise HTTPException(401 if token else 400, 'Sign-in failed. Check your details or confirm your email.')
        return response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, 'Account service is temporarily unavailable.') from None


def user_id(request):
    header = request.headers.get('authorization', '')
    if not header.startswith('Bearer ') or len(header) > 8192:
        raise HTTPException(401, 'Please sign in.')
    data = auth_request('user', token=header[7:])
    try:
        return str(UUID(data['id']))
    except (KeyError, ValueError, TypeError):
        raise HTTPException(401, 'Please sign in again.') from None


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class Order(BaseModel):
    symbol: str = Field(pattern=r'^[A-Z0-9_.-]{1,25}$')
    side: str = Field(pattern=r'^(buy|sell)$')
    quantity: int = Field(gt=0, le=1000000, strict=True)
    request_id: UUID


def install(app, database_request, market_snapshot, feed_error):
    @app.middleware('http')
    async def private_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(('/api/paper', '/api/account')):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.post('/api/account/{action}')
    def account(action: str, payload: Credentials):
        if action not in ('signup','login'):
            raise HTTPException(404)
        data = auth_request('signup' if action=='signup' else 'token?grant_type=password', payload.model_dump())
        # No refresh token persisted in the browser; users sign in again on expiry.
        return {'access_token':data.get('access_token'), 'expires_in':data.get('expires_in'),
                'confirmation_required':not bool(data.get('access_token'))}

    def ensure(uid):
        database_request('POST','dhanvest_paper_accounts',params={'on_conflict':'user_id'},
            body={'user_id':uid},prefer='resolution=ignore-duplicates,return=minimal')

    @app.get('/api/paper/portfolio')
    def portfolio(request: Request):
        uid = user_id(request); ensure(uid)
        account = database_request('GET','dhanvest_paper_accounts',params={'user_id':'eq.'+uid})[0]
        positions = database_request('GET','dhanvest_paper_positions',params={'user_id':'eq.'+uid,'quantity':'gt.0'})
        trades = database_request('GET','dhanvest_paper_trades',params={'user_id':'eq.'+uid,'order':'id.desc','limit':100})
        snapshot = None
        try:
            snapshot = market_snapshot()
        except feed_error:
            pass
        quotes = {q['symbol']:q for q in snapshot['quotes']} if snapshot else {}
        total = Decimal(str(account['cash'])); complete = True
        for pos in positions:
            q = quotes.get(pos['symbol'], {})
            price = q.get('price') or q.get('close')
            pos['mark_price'] = price
            pos['market_value'] = float(Decimal(str(price))*pos['quantity']) if price else None
            pos['unrealized_pnl'] = round(pos['market_value']-float(pos['cost_basis']),2) if price else None
            if price: total += Decimal(str(pos['market_value']))
            else: complete = False
        return {'account':account,'positions':positions,'trades':trades,
            'equity':float(total) if complete else None,
            'total_pnl':float(total-Decimal(str(account['initial_cash']))) if complete else None,
            'market':{'session':snapshot['session'],'retrieved_at':snapshot['retrieved_at']} if snapshot else None,
            'rules':{'fee_rate':0.0025,'settlement':'instant simulated settlement','virtual_money':True}}

    @app.post('/api/paper/orders')
    def order(payload: Order, request: Request):
        uid = user_id(request)
        # Retry of an already executed order must work even after the market closes.
        previous = database_request('GET','dhanvest_paper_trades',params={'user_id':'eq.'+uid,'request_id':'eq.'+str(payload.request_id)})
        if previous:
            trade = previous[0]
            if any(trade[k] != getattr(payload,k) for k in ('symbol','side','quantity')):
                raise HTTPException(409, 'Order reference was already used.')
            return {'trade':trade,'replayed':True}
        try:
            snapshot = market_snapshot()
        except feed_error:
            raise HTTPException(503, 'Fresh DSE prices are unavailable; no trade was executed.') from None
        now = datetime.now(timezone.utc)
        retrieved = datetime.fromisoformat(snapshot['retrieved_at'])
        age = (now-retrieved).total_seconds()
        if (not snapshot['session'].get('isOpen') or age < 0 or age > 120
            or snapshot['session'].get('sessionDate') != now.astimezone(ZoneInfo('Asia/Dhaka')).date().isoformat()):
            raise HTTPException(409, 'Market is closed or quote is stale. No trade was executed.')
        quote = next((q for q in snapshot['quotes'] if q['symbol']==payload.symbol),None)
        if not quote or not quote.get('traded') or not quote.get('price'):
            raise HTTPException(409, 'This equity has no executable DSE quote.')
        trade = database_request('POST','rpc/dhanvest_paper_order',body={'p_user':uid,
            'p_request':str(payload.request_id),'p_symbol':payload.symbol,'p_side':payload.side,
            'p_quantity':payload.quantity,'p_price':quote['price'],'p_date':quote['session_date'],
            'p_retrieved':snapshot['retrieved_at']})
        return {'trade':trade[0],'replayed':False}

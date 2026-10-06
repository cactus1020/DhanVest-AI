"""Local-only synthetic browser fixture. No real auth, money or database writes."""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from threading import Lock
from uuid import uuid4
from zoneinfo import ZoneInfo
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from frontend import paper_trading as paper
from frontend.market_data import FeedUnavailable

app=FastAPI(); accounts={}; holdings={}; receipts=[]; lock=Lock()
users={'qa-one@example.test':'11111111-1111-4111-8111-111111111111',
       'qa-two@example.test':'22222222-2222-4222-8222-222222222222'}

def auth(path,body=None,token=None):
    if token:
        if token not in users.values():raise HTTPException(401,'Please sign in.')
        return {'id':token}
    if body['email'] not in users or body['password']!='fixture-password':
        raise HTTPException(400,'Sign-in failed. Check your details.')
    return {'access_token':users[body['email']],'expires_in':3600}

def market():
    day=datetime.now(timezone.utc).astimezone(ZoneInfo('Asia/Dhaka')).date().isoformat()
    return {'session':{'isOpen':True,'sessionDate':day},'retrieved_at':datetime.now(timezone.utc).isoformat(),
            'quotes':[{'symbol':'TESTGP','price':250,'close':250,'traded':True,'session_date':day},
                      {'symbol':'TESTBANK','price':100,'close':100,'traded':True,'session_date':day}]}

def db(method,table,params=None,body=None,prefer=None):
    with lock:
        if table=='rpc/dhanvest_paper_order':
            uid=body['p_user'];symbol=body['p_symbol'];quantity=body['p_quantity'];side=body['p_side']
            account=accounts[uid];key=(uid,symbol);pos=holdings.get(key,{'symbol':symbol,'quantity':0,'cost_basis':0})
            gross=Decimal(str(body['p_price']))*quantity;fee=(gross*Decimal('.0025')).quantize(Decimal('.01'))
            cost=Decimal(str(pos['cost_basis']));realized=Decimal(0)
            if side=='buy':
                if account['cash']<gross+fee:raise HTTPException(409,'Not enough virtual cash.')
                account['cash']-=gross+fee;pos['quantity']+=quantity;pos['cost_basis']=float(cost+gross+fee)
            else:
                if pos['quantity']<quantity:raise HTTPException(409,'Insufficient shares.')
                removed=cost*quantity/pos['quantity'];realized=gross-fee-removed
                account['cash']+=gross-fee;pos['quantity']-=quantity;pos['cost_basis']=float(cost-removed)
            holdings[key]=pos
            trade={'id':len(receipts)+1,'user_id':uid,'request_id':body['p_request'],'symbol':symbol,'side':side,
                   'quantity':quantity,'price':body['p_price'],'fee':float(fee),'realized_pnl':float(realized),'created_at':datetime.now(timezone.utc).isoformat()}
            receipts.append(trade);return [trade.copy()]
        uid=(params or {}).get('user_id','eq.').removeprefix('eq.')
        if method=='POST':
            uid=body['user_id'];accounts.setdefault(uid,{'cash':Decimal(1000000),'initial_cash':1000000});return []
        if table.endswith('accounts'):return [dict(accounts[uid])]
        if table.endswith('positions'):return [p.copy() for (owner,_),p in holdings.items() if owner==uid and p['quantity']>0]
        if table.endswith('trades'):
            rows=[t.copy() for t in reversed(receipts) if t['user_id']==uid]
            request=(params or {}).get('request_id')
            return [t for t in rows if not request or t['request_id']==request.removeprefix('eq.')]
        return []

paper.auth_request=auth
paper.install(app,db,market,FeedUnavailable)
ROOT=Path(__file__).resolve().parents[1]/'frontend'
@app.get('/v2/practice')
def page():return FileResponse(ROOT/'practice.html')
@app.get('/api/market')
def quotes():return market()
app.mount('/assets',StaticFiles(directory=ROOT/'assets'),name='assets')

if __name__=='__main__':uvicorn.run(app,host='127.0.0.1',port=8002)

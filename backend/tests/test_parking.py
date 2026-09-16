import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from app.domain import price_cents, normalize_plate
from app.main import create_app
from app.models import Stay

@pytest.fixture
def system(tmp_path):
    tick=[1770000000]
    app=create_app(os.getenv('TEST_DATABASE_URL') or f'sqlite:///{tmp_path}/test.db',token='test-secret',demo=True,clock=lambda:tick[0])
    with TestClient(app) as c:
        if os.getenv('TEST_DATABASE_URL'):
            with app.state.sessions.begin() as db: db.query(Stay).delete()
        c.headers['Authorization']='Bearer test-secret'
        yield c,app,tick

@pytest.mark.parametrize('seconds,amount',[(0,0),(600,0),(601,1200),(3599,1200),(3600,1200),(3601,1800),(7200,1800),(7201,2400),(86400,15000)])
def test_billing(seconds,amount): assert price_cents(seconds,1200,600,10)==amount

@pytest.mark.parametrize('plate,expected',[('abc-1234','ABC1234'),(' abc1d23 ','ABC1D23')])
def test_plate(plate,expected): assert normalize_plate(plate)==expected

def test_invalid_plate():
    with pytest.raises(ValueError): normalize_plate('INVALID')

def test_auth(system):
    c,_,_=system;c.headers.clear()
    assert c.get('/api/overview').status_code==401
    assert c.post('/api/stays',json={'plate':'ABC1234'}).status_code==401

def test_lifecycle(system):
    c,_,tick=system
    r=c.post('/api/stays',json={'plate':'abc-1234','vehicle':'Civic','spot_id':3})
    assert r.status_code==201
    s=r.json();assert s['plate']=='ABC1234' and s['spot']=='A03'
    assert c.post('/api/stays',json={'plate':'ABC1234'}).status_code==409
    tick[0]+=3601
    assert c.get(f"/api/stays/{s['id']}/quote").json()['amount_cents']==1800
    body={'expected_cents':1800,'payment_method':'pix'}
    receipt=c.post(f"/api/stays/{s['id']}/checkout",json=body)
    assert receipt.status_code==200
    tick[0]+=4000
    assert c.post(f"/api/stays/{s['id']}/checkout",json=body).json()==receipt.json()
    overview=c.get('/api/overview').json()
    assert overview['occupied']==0 and overview['today_cents']==1800
    assert c.get('/api/history').json()['total']==1
    assert c.post('/api/stays',json={'plate':'ABC1234','spot_id':3}).status_code==201

def test_stale_quote(system):
    c,_,tick=system
    s=c.post('/api/stays',json={'plate':'ABC1234'}).json()
    tick[0]+=600
    assert c.get(f"/api/stays/{s['id']}/quote").json()['amount_cents']==0
    tick[0]+=1
    assert c.post(f"/api/stays/{s['id']}/checkout",json={'expected_cents':0}).status_code==409
    assert c.get('/api/overview').json()['occupied']==1

def test_full_lot(system):
    c,_,_=system
    for i in range(24): assert c.post('/api/stays',json={'plate':f'ABC{i:04}'}).status_code==201
    assert c.post('/api/stays',json={'plate':'DEF1234'}).status_code==409
    assert c.get('/api/overview').json()['occupied']==24

def test_invalid_input(system):
    c,_,_=system
    assert c.post('/api/stays',json={'plate':'?'}).status_code==422
    assert c.post('/api/stays',json={'plate':'ABC1234','spot_id':999}).status_code==409
    assert c.get('/api/stays/999/quote').status_code==404
    assert c.get('/api/history?page=0').status_code==422

def test_database_constraints(system):
    c,app,tick=system
    c.post('/api/stays',json={'plate':'ABC1234','spot_id':1})
    for plate,spot in [('ABC1234',2),('DEF1234',1)]:
        with pytest.raises(IntegrityError), app.state.sessions.begin() as db:
            db.add(Stay(plate=plate,vehicle='',spot_id=spot,entered_at=tick[0],first_hour=1200,extra_hour=600,grace_minutes=10))

def test_concurrent_entry(system):
    c,_,_=system
    def enter(plate): return c.post('/api/stays',json={'plate':plate,'spot_id':1}).status_code
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(enter,['ABC1234','DEF1234']))
    assert sorted(results)==[201,409]
    assert c.get('/api/overview').json()['occupied']==1

def test_history_csv(system):
    c,_,_=system
    for plate in ['ABC1234','DEF1234']:
        s=c.post('/api/stays',json={'plate':plate}).json()
        c.post(f"/api/stays/{s['id']}/checkout",json={'expected_cents':0,'payment_method':'cash'})
    assert c.get('/api/history?search=ABC').json()['total']==1
    assert c.get('/api/history?search=%25').json()['total']==0
    r=c.get('/api/history.csv')
    assert r.status_code==200 and 'ABC1234' in r.text and 'DEF1234' in r.text

def test_seed_not_destructive(system):
    c,_,_=system
    assert c.post('/api/demo').status_code==200
    assert c.post('/api/demo').status_code==409
    assert c.get('/api/overview').json()['occupied']==6

def test_secure_mode(tmp_path):
    with pytest.raises(RuntimeError): create_app(token='short',demo=False)
    app=create_app(f'sqlite:///{tmp_path}/secure.db',token='x'*32,demo=False)
    with TestClient(app) as c:
        assert c.post('/api/demo',headers={'Authorization':'Bearer '+'x'*32}).status_code==403

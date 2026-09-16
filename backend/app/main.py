import csv
import hmac
import io
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, select, func, update, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from .domain import normalize_plate, price_cents
from .models import Base, Spot, Stay

TZ = ZoneInfo('America/Sao_Paulo')


class Entry(BaseModel):
    plate: str
    vehicle: str = Field(default='', max_length=60)
    spot_id: int | None = Field(default=None, ge=1)

    @field_validator('plate')
    @classmethod
    def valid_plate(cls, value):
        return normalize_plate(value)


class Exit(BaseModel):
    expected_cents: int = Field(ge=0)
    payment_method: Literal['pix', 'card', 'cash'] = 'pix'


def create_app(database_url=None, token=None, demo=None, clock=None):
    demo = os.getenv('DEMO_MODE', 'true').lower() == 'true' if demo is None else demo
    token = token if token is not None else os.getenv('OPERATOR_TOKEN', 'demo-local' if demo else '')
    if not token or (not demo and len(token) < 24):
        raise RuntimeError('Defina OPERATOR_TOKEN com ao menos 24 caracteres fora do modo demo.')
    now = clock or (lambda: int(time.time()))
    engine = create_engine(database_url or os.getenv('DATABASE_URL', 'sqlite:///./parking.db'),
                           connect_args={'check_same_thread': False, 'timeout': 15}
                           if (database_url or os.getenv('DATABASE_URL', 'sqlite:///')).startswith('sqlite') else {})
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    sessions = sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_):
        Base.metadata.create_all(engine)
        with sessions.begin() as db:
            if not db.scalar(select(func.count()).select_from(Spot)):
                db.add_all([Spot(id=i, label=f'A{i:02}') for i in range(1, 25)])
        yield
        engine.dispose()

    app = FastAPI(title='Vaga Certa API', version='1.0.0', lifespan=lifespan)
    app.state.sessions = sessions
    app.state.now = now

    def auth(authorization: str = Header(default='')):
        if not hmac.compare_digest(authorization.encode(), f'Bearer {token}'.encode()):
            raise HTTPException(401, 'Acesso inválido. Confira o token do operador.')

    def db_session():
        with sessions() as db:
            yield db

    secured = [Depends(auth)]

    def serialize(stay, db):
        end = stay.exited_at if stay.exited_at is not None else now()
        amount = stay.amount_cents if stay.exited_at is not None else price_cents(
            max(0, end - stay.entered_at), stay.first_hour, stay.extra_hour, stay.grace_minutes)
        return dict(id=stay.id, plate=stay.plate, vehicle=stay.vehicle,
                    spot_id=stay.spot_id, spot=db.get(Spot, stay.spot_id).label,
                    entered_at=stay.entered_at, exited_at=stay.exited_at,
                    duration_seconds=max(0, end-stay.entered_at), amount_cents=amount,
                    payment_method=stay.payment_method)

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'demo': demo}

    @app.get('/api/overview', dependencies=secured)
    def overview(db=Depends(db_session)):
        active = list(db.scalars(select(Stay).where(Stay.exited_at.is_(None)).order_by(Stay.entered_at)))
        today = datetime.fromtimestamp(now(), TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        days = []
        for offset in range(6, -1, -1):
            start = today - timedelta(days=offset)
            finish = start + timedelta(days=1)
            amount = db.scalar(select(func.coalesce(func.sum(Stay.amount_cents), 0)).where(
                Stay.exited_at >= int(start.timestamp()), Stay.exited_at < int(finish.timestamp())))
            days.append({'date': start.strftime('%d/%m'), 'amount_cents': amount})
        occupied = {s.spot_id: s for s in active}
        spots = [{'id': s.id, 'label': s.label, 'plate': occupied[s.id].plate if s.id in occupied else None}
                 for s in db.scalars(select(Spot).order_by(Spot.id))]
        return {'demo': demo, 'capacity': len(spots), 'occupied': len(active),
                'today_cents': days[-1]['amount_cents'], 'revenue': days, 'spots': spots,
                'active': [serialize(s, db) for s in active],
                'tariff': {'first_hour': 1200, 'extra_hour': 600, 'grace_minutes': 10}}

    @app.post('/api/stays', status_code=201, dependencies=secured)
    def enter(payload: Entry, db=Depends(db_session)):
        if db.scalar(select(Stay.id).where(Stay.plate == payload.plate, Stay.exited_at.is_(None))):
            raise HTTPException(409, 'Esta placa já está no estacionamento.')
        occupied = select(Stay.spot_id).where(Stay.exited_at.is_(None))
        query = select(Spot).where(Spot.id.not_in(occupied)).order_by(Spot.id)
        if payload.spot_id:
            query = query.where(Spot.id == payload.spot_id)
        spot = db.scalar(query.limit(1))
        if not spot:
            raise HTTPException(409, 'Vaga indisponível ou estacionamento lotado.')
        stay = Stay(plate=payload.plate, vehicle=payload.vehicle.strip(), spot_id=spot.id,
                    entered_at=now(), first_hour=1200, extra_hour=600, grace_minutes=10)
        db.add(stay)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Outra entrada ocupou a vaga ou registrou esta placa. Tente novamente.')
        return serialize(stay, db)

    @app.get('/api/stays/{stay_id}/quote', dependencies=secured)
    def quote(stay_id: int, db=Depends(db_session)):
        stay = db.get(Stay, stay_id)
        if not stay:
            raise HTTPException(404, 'Estadia não encontrada.')
        return serialize(stay, db)

    @app.post('/api/stays/{stay_id}/checkout', dependencies=secured)
    def checkout(stay_id: int, payload: Exit, db=Depends(db_session)):
        stay = db.get(Stay, stay_id)
        if not stay:
            raise HTTPException(404, 'Estadia não encontrada.')
        if stay.exited_at is not None:
            return serialize(stay, db)  # Repetição da requisição não cobra duas vezes.
        end = now()
        amount = price_cents(max(0, end-stay.entered_at), stay.first_hour, stay.extra_hour, stay.grace_minutes)
        if payload.expected_cents != amount:
            raise HTTPException(409, 'O valor mudou. Atualize a prévia antes de confirmar.')
        db.execute(update(Stay).where(Stay.id == stay_id, Stay.exited_at.is_(None)).values(
            exited_at=end, amount_cents=amount, payment_method=payload.payment_method))
        db.commit()
        db.expire_all()
        return serialize(db.get(Stay, stay_id), db)

    @app.get('/api/history', dependencies=secured)
    def history(search: str = '', page: int = Query(1, ge=1), db=Depends(db_session)):
        base = select(Stay).where(Stay.exited_at.is_not(None))
        if search:
            base = base.where(Stay.plate.contains(search.upper().replace('-', ''), autoescape=True))
        total = db.scalar(select(func.count()).select_from(base.subquery()))
        rows = db.scalars(base.order_by(Stay.exited_at.desc(), Stay.id.desc()).offset((page-1)*20).limit(20))
        return {'total': total, 'page': page, 'items': [serialize(s, db) for s in rows]}

    @app.get('/api/history.csv', dependencies=secured)
    def export(db=Depends(db_session)):
        out = io.StringIO()
        writer = csv.writer(out, delimiter=';')
        writer.writerow(['Placa', 'Vaga', 'Entrada (São Paulo)', 'Saída (São Paulo)', 'Valor (centavos)', 'Forma'])
        for s in db.scalars(select(Stay).where(Stay.exited_at.is_not(None)).order_by(Stay.id)):
            writer.writerow([s.plate, db.get(Spot, s.spot_id).label,
                             datetime.fromtimestamp(s.entered_at, TZ).isoformat(),
                             datetime.fromtimestamp(s.exited_at, TZ).isoformat(), s.amount_cents, s.payment_method])
        return Response('\ufeff'+out.getvalue(), media_type='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=movimentacoes.csv'})

    @app.post('/api/demo', dependencies=secured)
    def seed(db=Depends(db_session)):
        if not demo:
            raise HTTPException(403, 'Demonstração desabilitada.')
        if db.scalar(select(func.count()).select_from(Stay)):
            raise HTTPException(409, 'Os dados de exemplo só podem ser carregados em um banco vazio.')
        current = now()
        for i, (plate, vehicle, minutes) in enumerate([
            ('ABC1D23', 'Honda Civic · prata', 82), ('DEF4G56', 'VW Polo · branco', 34),
            ('HIJ7K89', 'Fiat Argo · vermelho', 126), ('LMN1P23', 'Toyota Corolla · preto', 8),
            ('QRS4T56', 'Chevrolet Onix · azul', 53), ('UVW7X89', 'Hyundai HB20 · cinza', 211)]):
            db.add(Stay(plate=plate, vehicle=vehicle, spot_id=i+1, entered_at=current-minutes*60,
                        first_hour=1200, extra_hour=600, grace_minutes=10))
        for day in range(7):
            for j in range(3 + day % 3):
                end = current - day*86400 - (j+1)*1800
                db.add(Stay(plate=f'DEM{day}{j}00', vehicle='Veículo de demonstração', spot_id=24,
                            entered_at=end-7200, exited_at=end, first_hour=1200, extra_hour=600,
                            grace_minutes=10, amount_cents=1800, payment_method='pix'))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Dados já carregados por outra solicitação.')
        return {'message': 'Dados fictícios carregados.'}

    dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
    if dist.exists():
        app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')
        @app.get('/', include_in_schema=False)
        def index():
            return FileResponse(dist / 'index.html')
    return app


app = create_app()

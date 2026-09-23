from fastapi import APIRouter, HTTPException, Query, Response
from app import database
from app.services.forecast_service import forecast_service, records_csv

router = APIRouter(prefix='/api/forecasts', tags=['Forecasts'])

@router.get('/regions')
def regions():
    return {'regions': database.REGIONS}

@router.get('/chart')
@router.get('/table')
async def forecasts(region: str = 'ALL', refresh: bool = False):
    if region != 'ALL' and region not in database.REGIONS:
        raise HTTPException(400, '未知地區')
    return await forecast_service.get(region, refresh)

@router.get('/export/csv')
async def export(region: str = 'ALL'):
    data = await forecasts(region)
    return Response(records_csv(data['forecasts'], ['regionName','dataDate','minT','maxT','avgT']),
                    media_type='text/csv', headers={'Content-Disposition': 'attachment; filename=weekly_forecasts.csv'})

@router.get('/sql-query')
def query(query: str = Query(..., max_length=4000)):
    try:
        results = database.execute_raw_sql(query)
        return {'count': len(results), 'results': results, 'limit': 500}
    except Exception as exc:
        raise HTTPException(400, str(exc)) from None

from fastapi import APIRouter, HTTPException, Response
from app.sources import MAP_TILES, capabilities as source_capabilities
from app.services.weather_service import weather_service

router=APIRouter(prefix='/api/weather',tags=['Weather layers'])

@router.get('/capabilities')
def capabilities():
    checked=source_capabilities()
    supported={name:result.get('supported',False) for name,result in checked['sources'].items()}
    return {'supported':supported,'checked_at':checked.get('checked_at'),'map_tiles':MAP_TILES}

@router.get('/radar/image')
async def radar_image():
    await weather_service.get('radar')
    blob=weather_service.image()
    if blob is None:raise HTTPException(503,'雷達影像目前無法取得')
    return Response(blob,media_type='image/png',headers={'Cache-Control':'public, max-age=300'})

@router.get('/{product}')
async def weather_product(product:str,refresh:bool=False):
    if product not in ('rainfall','warnings','typhoon','radar','rainviewer','gfs_wind'):
        raise HTTPException(404,'未知圖層')
    return await weather_service.get(product,force=refresh)

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import requests
import redis.asyncio as redis
import json
from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager
import uvicorn

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis_client = redis.Redis(
        host=os.getenv("host"),
        port=os.getenv("port"),
        password=os.getenv("password"),
        decode_responses=True
    )
    try:
        await app.state.redis_client.ping()
        print("Connected to Redis successfully!")
        await FastAPILimiter.init(app.state.redis_client)
    except Exception as e:
        print(f"unable to connect to redis image: {e}")
        raise

    yield  
    await app.state.redis_client.close()
    print("closeed.")

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"Base route lo em untadi guru"}



@app.get(
    "/weather/{location}",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))]  
)
async def get_weather(location: str):
    redis_client: redis.Redis = app.state.redis_client
    cache_key = location.lower()
    cached_weather = await redis_client.get(cache_key)

    if cached_weather:
        status = "Using cached data from Redis"
        print(status)
        response = json.loads(cached_weather)
    else:
        api_key = os.getenv("api")
        url = (
            f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
            f"{location}?unitGroup=us&key={api_key}&contentType=json"
        )
        try:
            res = requests.get(url)
            res.raise_for_status()
        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Error fetching weather data: {e}")

        response = res.json()
        await redis_client.setex(cache_key, 3600, json.dumps(response))
        status = "Fetched from API and cached new data in Redis"
        print(status)

    current_weather = response.get("currentConditions", {})
    if not current_weather:
        raise HTTPException(status_code=404, detail="Weather data not found")

    weather_info = {
        "status": status,
        "temperature": f"{(current_weather['temp'] - 32) / 1.8:.2f} °C",
        "condition": current_weather.get("conditions"),
        "wind_speed": f"{current_weather.get('windspeed')} mph",
        "humidity": f"{current_weather.get('humidity')}%",
        "location": location
    }

    return JSONResponse(content=weather_info)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import re
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_API_URL = "http://localhost:11434/api/generate"

def clean_response(text):
    # Remove think tags and other XML-like tags
    cleaned = re.sub(r'<think>|</think>|<[^>]+>', '', text)
    # Remove extra newlines and spaces
    cleaned = re.sub(r'\n+', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Remove any non-printable characters
    cleaned = re.sub(r'[^\x20-\x7E\s]', '', cleaned)
    return cleaned.strip()

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get('user_message')
        
        if not user_message:
            raise HTTPException(status_code=400, detail="user_message is required")
        
        print(f"Received message: {user_message}")
        
        ollama_request = {
            "model": "deepseek-r1:1.5b",
            "prompt": user_message,
            "stream": False,  # Set to False to get complete response
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 150,
                "num_ctx": 512
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                ollama_response = await client.post(OLLAMA_API_URL, json=ollama_request)
                ollama_response.raise_for_status()
                
                response_data = ollama_response.json()
                bot_response = response_data.get('response', '')
                
                # Clean the response
                cleaned_response = clean_response(bot_response)
                print(f"Cleaned response: {cleaned_response}")
                
                if not cleaned_response:
                    raise HTTPException(
                        status_code=500,
                        detail="Empty response from model"
                    )
                
                return {"response": cleaned_response}
                
            except httpx.HTTPError as e:
                print(f"Ollama error: {str(e)}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to communicate with Ollama service: {str(e)}"
                )
            
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
async def test():
    """Test endpoint to verify Ollama connection"""
    try:
        test_request = {
            "model": "deepseek-r1:1.5b",
            "prompt": "Hi",
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(OLLAMA_API_URL, json=test_request)
            response_data = response.json()
            cleaned_response = clean_response(response_data.get('response', ''))
            
            return {
                "status": "success",
                "message": "API and Ollama connection working!",
                "test_response": cleaned_response
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": "API working, but cannot connect to Ollama",
            "detail": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    print("Starting server... Make sure Ollama is running and deepseek-r1:1.5b model is installed")
    uvicorn.run(app, host="0.0.0.0", port=8000)
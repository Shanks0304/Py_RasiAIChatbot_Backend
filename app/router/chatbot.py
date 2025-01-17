from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from supabase import create_client, Client

from app.utils.llm_query import create_prompt

from ..utils.embed import delete_vectors, embed_file, embed_text
from ..utils.get_user import get_current_user
from dotenv import load_dotenv
import httpx

load_dotenv()

# Initialize Supabase client
SUPABASE_PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_ANON_PUBLIC_KEY = os.getenv("SUPABASE_ANON_PUBLIC_KEY")
LLM_BEARER_TOKEN = os.getenv("LLM_BEARER_TOKEN")
supabase: Client = create_client(SUPABASE_PROJECT_URL, SUPABASE_ANON_PUBLIC_KEY)


router = APIRouter()

LLM_API_URL = {
    "csv": 'https://llm.rasi.ai/api/v1/upsert_csv',
    "docx": 'https://llm.rasi.ai/api/v1/upsert_doc',
    "pdf": 'https://llm.rasi.ai/api/v1/upsert_pdf',
    "json": 'https://llm.rasi.ai/api/v1/upsert_json',
    "txt": 'https://llm.rasi.ai/api/v1/upsert_txt',
    "xlsx": 'https://llm.rasi.ai/api/v1/upsert_excel',
    "pptx": 'https://llm.rasi.ai/api/v1/upsert_ppt',
}

extension_list = ["csv", "docx", "pdf", "json", "txt", "xlsx", "pptx"]

class AddChatbotRequest(BaseModel):
    chatbotName: str
    prompt: str

# async def embed_file(email = str, name = str, file = File):
#     file_contents =  await file.read()
#     file_extension = file.filename.split('.')[-1].lower()
#     file_to_send = ("files", (file.filename, file_contents, file.content_type))
#     file_name = file.filename

#     headers = {
#         "Authorization": f"Bearer {LLM_BEARER_TOKEN}"
#     }

#     data = {
#         "pineconeNamespace": f"{email}-{name}",
#         "tableName": f"{email}-{name}",
#         "namespace": f"{email}-{name}",
#         "metadata": f'{{"source": "{file_name}"}}'
#     }
#     print(data)
#     try:
#         async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=30.0)) as client:
#             api_response = await client.post(
#                 LLM_API_URL[file_extension],
#                 headers=headers,
#                 data=data,
#                 files=[file_to_send]
#             )
#             print("API Response:", api_response)
#             print("Response Status Code:", api_response.status_code)
#             print("Response Content:", api_response.text)
#         if api_response.status_code != 200:
#             print("here")  # Adjust `200` if your API uses different success codes
#             raise HTTPException(status_code=api_response.status_code, detail="Error Occurred")
#         return {'success': 'Upsert vector DB'}
#     except Exception as e:
#         raise HTTPException(status_code=501, detail=str(e))

@router.post("/add_chatbot")
async def add_chatbot(
    request: Request,
    response: Response,
    files: List[UploadFile] = File(...),
    chatbot_name: str = Form(...),
    business_name: str = Form(...),
    industry: str = Form(...),
    primary_language: str = Form(...),
    selected_functions: str = Form(...),
    communication_style: str = Form(...),
    user_data: Tuple[dict, Optional[str], Optional[str]] = Depends(get_current_user)
):
    current_user, updated_access_token, updated_refresh_token = user_data

    request.state.updated_access_token = updated_access_token
    request.state.updated_refresh_token = updated_refresh_token

    user_id = current_user.user.id
    # response = supabase.table("business_owner").select("email").eq('id', user_id).execute()

    # if not response.data:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # user_email = response.data[0]['email']
    # print(user_email)

    allowed_file_list = [
        file for file in files
        if file.filename.split('.')[-1].lower() in extension_list
    ]

    for file in allowed_file_list:
        await embed_file(chatbot_name=chatbot_name, file=file, token=user_id)
    

    prompt_text = await create_prompt(chatbot_name, business_name, industry, primary_language, selected_functions, communication_style, user_id)
    print(prompt_text)


    try:
        store_response = supabase.table('chatbot').insert(
            {
                'user_id': user_id, 
                'chatbotName': chatbot_name, 
                'prompt': prompt_text, 
                'upsert_filelist': [file.filename for file in allowed_file_list]
            }
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=501, detail=str(e))
    final_response = JSONResponse(content={'prompt': prompt_text})
    if updated_access_token and updated_refresh_token:
        is_production = os.getenv("ENV") == "production"
        print(is_production)
        if is_production:
            final_response.set_cookie(
                key="access_token",
                value=updated_access_token,
                httponly=False,
                secure=True,
                samesite="Lax",
                domain='.rasi.ai',
            )
            final_response.set_cookie(
                key="refresh_token",
                value=updated_refresh_token,
                httponly=False,
                secure=True,
                samesite="Lax",
                domain='.rasi.ai',
            )
        else:
            final_response.set_cookie(
                key="access_token",
                value=updated_access_token,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
            final_response.set_cookie(
                key="refresh_token",
                value=updated_refresh_token,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
    return final_response

@router.post("/upsert_file")
async def upsert_file(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    chatbotName: str = Form(...),
    user_data: Tuple[dict, Optional[str], Optional[str]] = Depends(get_current_user)
):
    current_user, updated_access_token, updated_refresh_token = user_data

    request.state.updated_access_token = updated_access_token
    request.state.updated_refresh_token = updated_refresh_token


    user_id = current_user.user.id
    # response = supabase.table("business_owner").select("email").eq('id', user_id).execute()

    # if not response.data:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # user_email = response.data[0]['email']

    embed_response = await embed_file(chatbot_name=chatbotName, file=file, token=user_id)
    
    try:
        store_response = supabase.rpc(
            'update_upsert_file_list',
            {
                'chatbot_name': chatbotName,
                'new_file': file.filename
            }
        ).execute()
        # return {"message": "File appended successfully"}
    except Exception as e:
        raise HTTPException(status_code=501, detail=str(e))
    
    final_response = JSONResponse(content={
        'status': 'success',
        'data': 'File uploaded successfully',
    })
    if updated_access_token and updated_refresh_token:
        is_production = os.getenv("ENV") == "production"
        print(is_production)
        if is_production:
            final_response.set_cookie(
                key="access_token",
                value=updated_access_token,
                httponly=False,
                secure=True,
                samesite="Lax",
                domain='.rasi.ai',
            )
            final_response.set_cookie(
                key="refresh_token",
                value=updated_refresh_token,
                httponly=False,
                secure=True,
                samesite="Lax",
                domain='.rasi.ai',
            )
        else:
            final_response.set_cookie(
                key="access_token",
                value=updated_access_token,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
            final_response.set_cookie(
                key="refresh_token",
                value=updated_refresh_token,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
    return final_response

@router.post("/upsert_text")
async def upsert_text(   
    request: Request,
    response: Response,
    text: str = Form(...),
    chatbotName: str = Form(...),
    user_data: Tuple[dict, Optional[str], Optional[str]] = Depends(get_current_user)
):
    current_user, updated_access_token, updated_refresh_token = user_data

    request.state.updated_access_token = updated_access_token
    request.state.updated_refresh_token = updated_refresh_token


    user_id = current_user.user.id
    # response = supabase.table("business_owner").select("email").eq('id', user_id).execute()

    # if not response.data:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # user_email = response.data[0]['email']

    embed_response = await embed_text(name=chatbotName, text=text, token=user_id)
    
    try:
        store_response = supabase.rpc(
            'update_upsert_text',
            {
                'chatbot_name': chatbotName,
                'updatedtext': text
            }
        ).execute()
        # return {"message": "File appended successfully"}
    except Exception as e:
        raise HTTPException(status_code=501, detail=str(e))
    
    final_response = JSONResponse(content={
        'status': 'success',
        'data': 'File uploaded successfully',
    })
    if updated_access_token and updated_refresh_token:
        is_production = os.getenv("ENV") == "production"
        print(is_production)
        if is_production:
            final_response.set_cookie(
                key="access_token",
                value=updated_access_token,
                httponly=False,
                secure=True,
                samesite="Lax",
                domain='.rasi.ai',
            )
            final_response.set_cookie(
                key="refresh_token",
                value=updated_refresh_token,
                httponly=False,
                secure=True,
                samesite="Lax",
                domain='.rasi.ai',
            )
        else:
            final_response.set_cookie(
                key="access_token",
                value=updated_access_token,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
            final_response.set_cookie(
                key="refresh_token",
                value=updated_refresh_token,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
    return final_response

@router.post("/get_chatbots")
async def get_chatbots(
    user_data: Tuple[dict, Optional[str], Optional[str]] = Depends(get_current_user)
):
    current_user, updated_access_token, updated_refresh_token = user_data
    user_id = current_user.user.id
    response = supabase.table("chatbot").select("*").eq('user_id', user_id).execute()
    print(response.data)
    final_response = JSONResponse(content=response.data)
    if updated_access_token and updated_refresh_token:
        is_production = os.getenv("ENV") == "production"
        print(is_production)
        if is_production:
            final_response.set_cookie(
                key="access_token",
                value=updated_access_token,
                httponly=False,
                secure=True,
                samesite="Lax",
                domain='.rasi.ai',
            )
            final_response.set_cookie(
                key="refresh_token",
                value=updated_refresh_token,
                httponly=False,
                secure=True,
                samesite="Lax",
                domain='.rasi.ai',
            )
        else:
            final_response.set_cookie(
                key="access_token",
                value=updated_access_token,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
            final_response.set_cookie(
                key="refresh_token",
                value=updated_refresh_token,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
    return final_response

@router.post("/delete_chatbot")
async def delete_chatbot(
    request: Request,
    response: Response, 
    chatbot_name: str = Form(...),
    user_data: Tuple[dict, Optional[str], Optional[str]] = Depends(get_current_user)
):
    current_user, updated_access_token, updated_refresh_token = user_data

    request.state.updated_access_token = updated_access_token
    request.state.updated_refresh_token = updated_refresh_token


    user_id = current_user.user.id

    # delete_all_chat_histories
    chat_response = supabase.table("test_chat_history").delete().eq('chatbotName', chatbot_name).eq('user_id', user_id).execute()

    # delete_chatbot
    bot_response = supabase.table("chatbot").delete().eq('chatbotName', chatbot_name).eq('user_id', user_id).execute()

    # delete_vectors
    delete_response = await delete_vectors(chatbot_name, user_id)

    final_response = JSONResponse(content={
        'status': 'success',
        'data': 'Chatbot is deleted successfully',
    })
    if updated_access_token and updated_refresh_token:
        is_production = os.getenv("ENV") == "production"
        print(is_production)
        if is_production:
            final_response.set_cookie(
                key="access_token",
                value=updated_access_token,
                httponly=False,
                secure=True,
                samesite="Lax",
                domain='.rasi.ai',
            )
            final_response.set_cookie(
                key="refresh_token",
                value=updated_refresh_token,
                httponly=False,
                secure=True,
                samesite="Lax",
                domain='.rasi.ai',
            )
        else:
            final_response.set_cookie(
                key="access_token",
                value=updated_access_token,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
            final_response.set_cookie(
                key="refresh_token",
                value=updated_refresh_token,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
    return final_response

@router.post("/delete_vectors")
async def delete_upsertfile(
    request: Request,
    response: Response,
    chatbot_name: str = Form(...),
    user_data: Tuple[dict, Optional[str], Optional[str]] = Depends(get_current_user)
):
    current_user, updated_access_token, updated_refresh_token = user_data

    request.state.updated_access_token = updated_access_token
    request.state.updated_refresh_token = updated_refresh_token


    user_id = current_user.user.id

    #delete the upsert_filelist on table
    bot_response = supabase.table("chatbot").update({
        "upsert_filelist": None
    }).eq('chatbotName', chatbot_name).eq('user_id', user_id).execute()

    # delete_vectors
    delete_response = await delete_vectors(chatbot_name, user_id)

    final_response = JSONResponse(content={
        'status': 'success',
        'data': 'Upserted files are deleted successfully',
    })
    if updated_access_token and updated_refresh_token:
        is_production = os.getenv("ENV") == "production"
        print(is_production)
        if is_production:
            final_response.set_cookie(
                key="access_token",
                value=updated_access_token,
                httponly=False,
                secure=True,
                samesite="Lax",
                domain='.rasi.ai',
            )
            final_response.set_cookie(
                key="refresh_token",
                value=updated_refresh_token,
                httponly=False,
                secure=True,
                samesite="Lax",
                domain='.rasi.ai',
            )
        else:
            final_response.set_cookie(
                key="access_token",
                value=updated_access_token,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
            final_response.set_cookie(
                key="refresh_token",
                value=updated_refresh_token,
                httponly=False,
                secure=False,
                samesite="Lax",
            )
    return final_response
    
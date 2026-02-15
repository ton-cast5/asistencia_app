# database/supabase_client.py
import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("❌ FALTAN CREDENCIALES: Revisa tu archivo .env")
        
        self.headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'  # Importante para que devuelva el objeto creado
        }
    
    def query(self, table, method='GET', data=None, params=None):
        url = f"{self.url}/rest/v1/{table}"
        print(f"🔌 URL: {url}")
        print(f"📤 Method: {method}")
        if data:
            print(f"📦 Data: {data}")
        if params:
            print(f"🔍 Params: {params}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=data, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers, params=params)
            
            print(f"📥 Status Code: {response.status_code}")
            print(f"📥 Response: {response.text[:200]}")  # Primeros 200 caracteres
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error en petición: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"❌ Response error: {e.response.text}")
            return None
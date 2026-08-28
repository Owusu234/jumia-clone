from supabase import create_client, Client
from django.conf import settings

def get_supabase_client() -> Client:
    """Initialize and return Supabase client"""
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise ValueError("Supabase URL and Anon Key must be set in environment variables")
    
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
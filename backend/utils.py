# In your_app/utils.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import traceback
import json

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Get request details
    request = context.get('request')
    view = context.get('view')

    if response is not None:
        # Print detailed error information
        print("\n" + "="*80)
        print(f"🔴 API ERROR - Status Code: {response.status_code}")
        print("="*80)

        # Request details
        if request:
            print(f"\n📍 Request Info:")
            print(f"   Method: {request.method}")
            print(f"   Path: {request.path}")
            print(f"   User: {request.user if hasattr(request, 'user') else 'Anonymous'}")

            # Request body
            if hasattr(request, 'data') and request.data:
                print(f"\n📝 Request Body:")
                try:
                    print(f"   {json.dumps(request.data, indent=2)}")
                except:
                    print(f"   {request.data}")

        # View details
        if view:
            print(f"\n🎯 View: {view.__class__.__name__}")

        # Exception details
        print(f"\n❌ Exception Type: {exc.__class__.__name__}")
        print(f"   Exception Message: {str(exc)}")

        # Response error details
        print(f"\n📤 Response Error Details:")
        try:
            print(f"   {json.dumps(response.data, indent=2)}")
        except:
            print(f"   {response.data}")

        # Full traceback for debugging
        if response.status_code >= 500 or response.status_code == 400:
            print(f"\n🔍 Full Traceback:")
            traceback.print_exc()

        print("="*80 + "\n")

    return response
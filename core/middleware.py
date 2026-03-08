from django.http import Http404
from django.shortcuts import render
from django.urls import resolve, Resolver404


class Custom404Middleware:
    """
    Middleware to show custom 404 page for invalid URLs
    even when DEBUG = True
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        try:
            # Try to resolve the URL
            resolve(request.path)
        except Resolver404:
            # If URL is not found, render custom 404 page
            return render(request, '404.html', status=404)
        
        # If URL is valid, proceed normally
        response = self.get_response(request)
        return response

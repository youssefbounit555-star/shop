from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError


def custom_404_view(request, exception=None):
    """
    Custom 404 error handler view.
    """
    return render(request, '404.html', status=404)


def custom_500_view(request):
    """
    Custom 500 error handler view.
    """
    return render(request, '500.html', status=500)


# Development testing views
def test_404_view(request):
    """
    Test 404 page during development.
    Visit: /test-404/
    """
    return custom_404_view(request)


def test_500_view(request):
    """
    Test 500 page during development.
    Visit: /test-500/
    """
    return custom_500_view(request)

from django.http import HttpResponse
from django.shortcuts import render

def index (request):
    return  render(request, 'index.html')

def removepunc(request):
    #getting the text and the putting it in a variable
    newtext = (request.GET.get('text', 'default'))
    print (newtext)
    return HttpResponse(
        f'remove punc </br> <a href = "/">back to home</a> </br> This is the text that was entered: {newtext}'
        )

def capfirst(request):
    return HttpResponse(
        f'remove punc </br>'
        f'<a href = "/">back to home</a>'
        )

def newlineremove(request):
    return HttpResponse(
        f'remove punc </br>'
        f'<a href = "/">back to home</a>'
        )

def spaceremove(request):
    return HttpResponse(
        f'remove punc </br>'
        f'<a href = "/">back to home</a>'
        )

def charcount(request):
    return HttpResponse(
        f'remove punc </br>'
        f'<a href = "/">back to home</a>'
        )




from django.http import HttpResponse
from django.shortcuts import render


def index(request):
    return render(request, 'index.html')


def analyze(request):
    # getting the text and the putting it in a variable

    newtext = (request.GET.get('text', 'default'))
    removepunc = request.GET.get('removepunc', 'off')

    print(removepunc)  # true/false
    print(newtext)

    analyzed = ""
    puncs = '''!"#$%&'()*+, -./:;<=>?@[\]^_`{|}~'''

    if removepunc == 'on':
        for char in newtext:
            if char not in puncs:
                analyzed += char

        params = {'purpose': "is free from punctuation", 'analyzed_text': analyzed}
        return render(request, 'analyze.html', params)
    
    elif removepunc == 'off':
        return HttpResponse(f'Since You forgot to mark the checkbox, nothing changes <h1>{newtext}</h1>')

    # we'll use a template instead of httpRespose

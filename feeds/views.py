from django.shortcuts import render, redirect, render_to_response
from django.http import HttpResponse, JsonResponse
import ConfigParser
# Create your views here.
config = ConfigParser.RawConfigParser()
config.read('keys.cfg')
import tweepy
from tasks import *
from django.core.urlresolvers import reverse

session = {}

def index(request):
    return render_to_response('layout.html')

def get_opml(request):
    auth = tweepy.OAuthHandler(config.get('twitter', 'consumer_key'), config.get('twitter', 'consumer_secret'), 'http://'+request.get_host()+'/verify/')
    try: 
        #get the request tokens
        redirect_url= auth.get_authorization_url()
        session['request_token'] = auth.request_token
    except tweepy.TweepError:
        print 'Error! Failed to get request token'
    return redirect(redirect_url) 

def get_verification(request):
    #get the verifier key from the request url
    verifier= request.GET.get('oauth_verifier')
    if 'request_token' not in session:
        return redirect('/') 
    token = session['request_token']
    job = opml_task.apply_async([token, verifier, 'http://'+request.get_host()])
    session.pop('request_token')
    return render_to_response('layout.html', context={'uuid':'%s'%job.id})

def get_status(request):
    #get the verifier key from the request url
    task_id = request.GET.get('uuid')
    task = opml_task.AsyncResult(task_id)
    if task.state == 'PROGRESS':
        return JsonResponse({'task_status':task.state, 'info':task.info['info'], 'count':task.info['count'], 'total_count':task.info['total']})
    elif task.state == 'FAILURE':
        return JsonResponse({'task_status':task.state,}, status=400)
    elif task.state == 'SUCCESS':
        return JsonResponse({'task_status':task.state})
    else:
        return JsonResponse({'task_status':task.state, 'message':'It is lost'})


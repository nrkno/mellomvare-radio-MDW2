#! /usr/bin/env python
# -*- coding: utf-8 -*-
#from wsgiref.simple_server import make_server
#import pylibs.dab

# TODO: Få satt riktig PYTHONPATH

import traceback
from os import environ
from sys import exc_info
import annonser
from dab import error, OK, main

QUARK_NAME='MDW2'

def application(web_environ, start_response):
    
    body_parts = []
    try:
        request_body_size = int(web_environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
        request_body_size = 0
    request_body = web_environ['wsgi.input'].read(request_body_size)

    try:
        respons = main(request_body)
    except:
        type, val, tb = exc_info()
        msg = "".join(traceback.format_exception(type, val, tb))
        body_parts.append(error("dab10", QUARK_NAME, melding=msg))
    else:
        #Svar til sender
        body_parts.append(respons)
    #response_body = 'Request method: %s' % environ['REQUEST_METHOD']
    #body_parts.append(body_parts)
    #body_parts.append(repr(request_body))
    #body_parts.append(repr(web_environ))
    #body_parts.append(annonser.spiller[0])
    #body_parts.append("ERT")
    
    response_body = "\n".join(body_parts).encode('utf-8')
    
    status = '200 OK'
    response_headers = [
        ('Content-Type', 'text/plain'),
        ('Content-Length', str(len(response_body)))
    ]
    start_response(status, response_headers)
    
    return [response_body]



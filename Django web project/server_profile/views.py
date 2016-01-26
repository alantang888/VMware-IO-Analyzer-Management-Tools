from django.shortcuts import render
from django.http import HttpResponse, HttpResponseServerError, HttpResponseForbidden
from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.utils.http import urlunquote
from server_profile.models import Server, Result
import re
import json
import datetime

# Create your views here.
def get_active_server_and_profile(request):
    header_regex = re.compile("^(?P<key>.*):\s+(?P<value>.*)$")
    active_servers_list = []
    
    active_servers_query = Server.objects.filter(active=True)
    for server in active_servers_query:
        temp = {}
        temp["serverName"] = server.name
        temp["url"] = server.url
        temp["profile"] = {}
        for p in server.profile_set.filter(active=True):
            temp["profile"][p.name] = p.http_post_payload
                
        temp["headers"] = {}
        for line in server.http_headers.splitlines():
                re_result = header_regex.search(line)
                if re_result:
                    temp["headers"][re_result.group("key")] = \
                    re_result.group("value")
        
        active_servers_list.append(temp)
        
    return HttpResponse(json.dumps(active_servers_list))
   
def upload_test_result(request):
    if not request.method == "POST":
        return HttpResponseForbidden("Only support HTTP POST.")
    
    posted_result = json.loads(request.body)
    tested_server = None
    try:
        tested_server = Server.objects.get(name=posted_result["server_name"])
    except ObjectDoesNotExist as e:
        return HttpResponseServerError("Server does not exist, detail:{}".format(e.message))
    
    del posted_result["server_name"]
    posted_result["report_time"] = datetime.datetime.fromtimestamp(posted_result["report_time"])
    test_result = Result(server=tested_server, **posted_result)
    try:
        test_result.save()
    except IntegrityError as e:
        return HttpResponseServerError("Insert DB error, detail:{}".format(e.message))
    
    return HttpResponse("OK")

def result_list(request):
    results = Result.objects.order_by("server", "report_time")
    return render(request, "result_list.html", locals())

def server_list(request):
    servers = Server.objects.order_by("name")
    return render(request, "server_list.html", locals())

def test_vm_list(request, server_name):
    server_name = urlunquote(server_name)
    test_vms =  Result.objects.filter(server__name = server_name).values('test_vm').order_by("test_vm").distinct()
    return render(request, "test_vm_list.html", locals())

def test_profile_list(request, server_name, test_vm):
    server_name = urlunquote(server_name)
    test_vm = urlunquote(test_vm)
    test_specs = Result.objects.filter(server__name = server_name, test_vm = test_vm).values('test_spec').order_by("test_spec").distinct()
    return render(request, "test_profile_list.html", locals())
    
def display_test_profile_result(request, server_name, test_vm, test_spec):
    server_name = urlunquote(server_name)
    test_vm = urlunquote(test_vm)
    test_spec = urlunquote(test_spec)
    iops_datas = Result.objects.filter(server__name = server_name, test_vm = test_vm, test_spec= test_spec).order_by("report_time").values_list("report_time","total_iops", "read_iops", "write_iops")
    latency_datas = Result.objects.filter(server__name = server_name, test_vm = test_vm, test_spec= test_spec).order_by("report_time").values_list("report_time","avg_read_latency", "avg_write_latency")
    
    iops_init_end_date = iops_datas.last()[0]
    iops_init_start_date = iops_init_end_date - datetime.timedelta(7)
    latency_init_end_date = latency_datas.last()[0]
    latency_init_start_date = latency_init_end_date - datetime.timedelta(7)
    
    return render(request, "display_test_profile_result.html", locals())
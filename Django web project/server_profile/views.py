from django.shortcuts import render
from django.http import HttpResponse, HttpResponseServerError, HttpResponseForbidden
from django.db import IntegrityError
from django.db.models import Max
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.http import urlunquote
from server_profile.models import Server, Result, Profile
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
    client_ip_addr = request.META["REMOTE_ADDR"]
    try:
        tested_server = Server.objects.get(url__contains=client_ip_addr)
    except ObjectDoesNotExist as e:
        return HttpResponseServerError("Server does not exist, detail:{}".format(e.message))
    
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

def check_active_profile_run_status(request):
    active_profiles = Profile.objects.filter(active=True).values("server__name", "name", "http_post_payload")
    last_result = Result.objects.values("server__name", "test_vm", "test_spec").annotate(Max("report_time"))
    
    check_result = {"result":"OK", "error_message":""}
    
    for p in active_profiles:
        for r in last_result:
            if r["server__name"] != p["server__name"]:
                continue
            if r["test_spec"].replace("%","").lower() not in p["http_post_payload"]:
                continue
            if p["name"].split("-")[0] not in r["test_vm"]:
                continue
            
            delta = timezone.now() - r["report_time__max"]
            # check if the last test is over 2 hours will report error
            if delta.seconds > 3600 * 2:
                check_result["result"] = "ERROR"
                check_result["error_message"] += "Server {!r} profile {!r} last result over 2 hours.\n".format(p["server__name"], p["name"])
                break
            else:
                break
        else:
            check_result["result"] = "ERROR"
            check_result["error_message"] += "Server {!r} profile {!r} no test result found.\n".format(p["server__name"], p["name"])
            
    return HttpResponse(json.dumps(check_result))
    
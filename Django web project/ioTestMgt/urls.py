"""ioTestMgt URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from server_profile.views import get_active_server_and_profile, upload_test_result, result_list, server_list, test_vm_list, test_profile_list, display_test_profile_result, check_active_profile_run_status, get_result_by_test_spec, test_spec_result_list, gen_aggregate_report_link, get_test_aggregate_report 

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r"^server_profile/", get_active_server_and_profile),
    url(r"^result_upload/", upload_test_result),
    url(r"^result_list/", result_list),
    url(r"^check_result/$", server_list, name="server_list"),
    url(r"^check_result/(?P<server_name>[^/]*)/$", test_vm_list, name="test_vm_list"),
    url(r"^check_result/(?P<server_name>[^/]*)/(?P<test_vm>[^/]*)/$", test_profile_list, name="test_profile_list"),
    url(r"^check_result/(?P<server_name>[^/]*)/(?P<test_vm>[^/]*)/(?P<test_spec>[^/]*)/$", display_test_profile_result, name="display_test_profile_result"),
    url(r"^check_active_profile_run_status/$", check_active_profile_run_status),
    url(r"^get_result_by_test_spec/$", get_result_by_test_spec),
    url(r"^test_spec_result_list/(?P<test_spec>[^/]*)/(?:(?P<number_of_day>\d+)/)?$", test_spec_result_list, name="test_spec_report"),
    url(r"^get_test_aggregate_report/$", gen_aggregate_report_link),
    url(r"^get_test_aggregate_report/(?P<start_time_str>\d{4}-\d{2}-\d{2})/(?P<end_time_str>\d{4}-\d{2}-\d{2})/$", get_test_aggregate_report, name="get_test_aggregate_report"),
]

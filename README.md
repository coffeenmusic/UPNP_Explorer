# :books:References
- ["Exploring UPnP with Python" - Electric Monk](https://www.electricmonk.nl/log/2016/07/05/exploring-upnp-with-python/)
  - A lot of the SSDP code is a direct copy from this reference
- [upnpclient](https://github.com/flyte/upnpclient/blob/develop/upnpclient/soap.py)
  - A lot of the SOAP request code is a combination of this reference and the first reference
  
# Motivation
I just wanted to play around with UPNP device discovery. I'm sure you can find better code out there, but I do like the way I condensed down the Action and Argument definitions so it is really easy to see what is available.

# :abc: Getting Started
Look at the Example.ipynb to see the commands necessary. The jupyter notebook is more descriptive than the README overview below. Also the output looks much cleaner in the Jupyter Notebook.

# :scroll: Quick Overview
Step 1: Broadcast
```
upnp = UPNP_Explorer() # Broadcast to UPNP Devices
upnp.SSDP.print_servers()
```
>Samsung-Linux/4.1, UPnP/1.0, Samsung_UPnP_SDK/1.0_0  
http/1.1 200 ok: HTTP/1.1 200 OK  
cache-control: max-age=1800  
date: Wed, 15 Jul 2020 18:01:31 GMT  
location: http://192.168.1.14:9197/dmr  
st: upnp:rootdevice  
usn: uuid:036cb031-f5f8-4831-bcd7-c0259ee25740::upnp:rootdevice  
content-length: 0  
bootid.upnp.org: 4  
	
Step 2: Define Server
```
url_list = upnp.define_server('samsung')
```
		
Step 3a: Choose URL Set (Devices can have more than one set of URLs)
```
USE_IDX = 0
CTRL_URL = upnp.SCPD.url_list[USE_IDX]['ctrl']
SCPD_URL = upnp.SCPD.url_list[USE_IDX]['scpd']
SERVICE_TYPE = upnp.SCPD.url_list[USE_IDX]['type']
```
Step 3b: Get the Service XML
```
upnp.SCPD.get_service_xml(SCPD_URL)
```
Step 4a: Define Actions and Input Arguments
```
upnp.SCPD.pretty_print_actions()
```
>    ListPresets(InstanceID)  
&nbsp;&nbsp;&nbsp;&nbsp;Returns: (CurrentPresetNameList)  
SelectPreset(InstanceID, PresetName)  
GetMute(InstanceID, Channel)  
&nbsp;&nbsp;&nbsp;&nbsp;Returns: (CurrentMute)  
SetMute(InstanceID, Channel, DesiredMute)  
GetVolume(InstanceID, Channel)  
&nbsp;&nbsp;&nbsp;&nbsp;Returns: (CurrentVolume)  
    SetVolume(InstanceID, Channel, DesiredVolume)  
```
upnp.SCPD.print_action_arg_desc(ACTION_NAME)
```
>InstanceID  
&nbsp;&nbsp;&nbsp;&nbsp;dataType: ui4  
Channel  
&nbsp;&nbsp;&nbsp;&nbsp;dataType: string  
&nbsp;&nbsp;&nbsp;&nbsp;allowedValueList: Master  
DesiredMute  
&nbsp;&nbsp;&nbsp;&nbsp;dataType: boolean  
```
argument_inputs = upnp.SCPD.define_action('SetMute')
print(upnp.SCPD.input_args)
```
>{'InstanceID': 0, 'Channel': 'Master', 'DesiredMute': None}
	
Step 4b: Change any input action values if necessary or desired
```
argument_inputs['DesiredMute'] = 1
```
Step 5: 
```
upnp.request_action(CTRL_URL, SERVICE_TYPE) # ACTION_NAME & INPUT_ARGS defined from SCPD.define_action
upnp.print_xml(upnp.SOAP.response)
```
><?xml version="1.0" ?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
	<s:Body>
		<u:SetMuteResponse xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1"/>
	</s:Body>
</s:Envelope>
import socket
from lxml import etree
from io import StringIO, BytesIO
import requests
from urllib.parse import urljoin
import xml.dom.minidom

class UPNP_Explorer:
    def __init__(self):
        # Broadcast to UPNP Servers & Get Response
        self.SSDP = UPNP_SSDP()
        
    def define_server(self, server_name):
        self.server_name = server_name
        
        # Get location url for specified server
        self.location_url = self.SSDP.get_property_dict(server_name)['location']
        
        self.SCPD = UPNP_SCPD(server_name, self.location_url)
        
    def request_action(self, ctrl_url, service_type, action_name=None, input_args=None):
        if action_name == None:
            action_name = self.SCPD.action_name
            
        if input_args == None:
            input_args = self.SCPD.input_args
            
        self.SOAP = UPNP_SOAP(ctrl_url, service_type, action_name, input_args)
        
    def print_element_pretty(self, obj, tab_cnt=0, filter_txt='', filter_tag='', filter_prt_tag=''):        
        for v in obj.getchildren():
            v_str = '' if v.text == None else v.text.strip()
            t_str = v.tag.split('}')[-1] if '}' in v.tag else v.tag
            if filter_txt.lower() in v_str.lower() and filter_tag.lower() in t_str.lower() and filter_prt_tag.lower() in v.getparent().tag:
                print(''.join(['\t']*tab_cnt)+t_str+'--> '+v_str)

            tab_cnt += 1
            tab_cnt = self.print_element_pretty(v, tab_cnt=tab_cnt, filter_txt=filter_txt, filter_tag=filter_tag)
        tab_cnt -= 1
        
        if tab_cnt < 0:
            return
        return tab_cnt

    def print_xml(self, xml_str):
        print(xml.dom.minidom.parseString(xml_str).toprettyxml())


class UPNP_SSDP:
    UPNP_BROADCAST_PORT = 1900
    UPNP_BROADCAST_IP = '239.255.255.250'
    UPNP_BRADCAST_MSG = \
            'M-SEARCH * HTTP/1.1\r\n' \
            'HOST:239.255.255.250:1900\r\n' \
            'ST:upnp:rootdevice\r\n' \
            'MX:2\r\n' \
            'MAN:"ssdp:discover"\r\n' \
            '\r\n'
    
    def __init__(self, print_broadcast=False):
        self.print_broadcast = print_broadcast
        self.broadcast()
        
    def broadcast(self, socket_timeout=2, buffer_size=4096):
        # Set up UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.settimeout(socket_timeout)
        s.sendto(str.encode(self.UPNP_BRADCAST_MSG), (self.UPNP_BROADCAST_IP, self.UPNP_BROADCAST_PORT))
        
        self.servers = {}
        try:
            while True:
                data, addr = s.recvfrom(buffer_size)
                server, property_dict = self.get_response_dict(data.decode())

                server += '_0'
                if server in self.servers.keys():
                    cnt = int(server.split('_')[-1]) + 1
                    server = server[:-len(str(cnt-1))] + str(cnt)        

                self.servers[server] = property_dict
                if self.print_broadcast:
                    print(addr)
                    print(data.decode())
        except socket.timeout:
            pass
        
    def get_response_dict(self, data_str):
		"""
		Formats SSDP Response from UPNP Devices to a dictionary of server properties
		- data_str: device response
		
		return server_name, response_dict
		"""
	
        property_dict = {}
        server = ''
        for line in data_str.split('\r\n'):
            if line.lower().startswith('server:'):
                server = line[len('server: '):]
            else:
                k = line.split(': ')[0].lower()
                v = line.split(': ')[-1]

                if k != '' and v != '':
                    property_dict[k] = v

        return server, property_dict
    
    def get_property_dict(self, server_name, server_idx=0):
	    """
		- server_name: server name does not have to match exacty, but the entire search str must exist in servers' key
		- server_idx: if more than one server are found with server_name, then the index is used to pick which server
		
		returns all properties for given server as property dictionary
		"""
	
        assert len(self.servers) > 0, 'Error: servers dictionary empty.'
        server_key = [k for k in self.servers.keys() if server_name.lower() in k.lower()]
        assert len(server_key) > 0, 'Error: No server with specified key word found.'
        if len(server_key) > 1:
            print('Multiple servers found for server name (%s). Please use server_idx input argument to specify which server ' \
                  'to use or be more specific when specifying server_name. %s index currently used.'%(server_name, server_idx))              
            print('Servers found:\r\n', ''.join(['\t%s\r\n'%(s) for s in server_key]))
        
        if len(server_key) >= server_idx:
            server_idx = 0
        server_key = server_key[server_idx]

        return self.servers[server_key]
    
    def print_servers(self):
        for server, values in self.servers.items():
            print(server)
            for k, v in values.items():
                print('\t%s: %s'%(k,v))
            print()        
        
class UPNP_SCPD:
    def __init__(self, server_name, location_url):
        self.server_name = server_name
        self.location_url = location_url
        
        # Get SCPD Root XML as ElementTree Element
        response = requests.get(self.location_url)
        self.root = etree.fromstring(response.content, base_url=self.location_url)
        
        # Get service URLs
        self.url_list = self.get_service_urls()
        
    
    def get_service_xml(self, scpd_url):
        response = requests.get(scpd_url)
        self.service_root = etree.fromstring(response.content, base_url=scpd_url)
        
    def get_service_urls(self):
        # Get Base URL
        urlbase = self._filter_etree(self.root, filter_tag='urlbase')
        if len(urlbase) >= 1:
            self.url_soap_req_base = urlbase[0].text
        else:
            self.url_soap_req_base = ':'.join(self.location_url.split(':')[:-1]) + ':' + self.location_url.split(':')[-1].split('/')[0]

        burl = self.url_soap_req_base
        
        # Get Service URLs    
        ctrl = self._filter_etree(self.root, filter_prt_tag='service', filter_tag='controlurl')
        scpd = self._filter_etree(self.root, filter_prt_tag='service', filter_tag='scpdurl')
        stype = self._filter_etree(self.root, filter_prt_tag='service', filter_tag='servicetype')

        self.url_list = []
        for c, s, st in zip(ctrl, scpd, stype):
            url_dict = dict({'ctrl': urljoin(burl, c.text), 'scpd': urljoin(burl, s.text), 'type': st.text})
            self.url_list += [url_dict]      
        return self.url_list
    
    def _filter_etree(self, obj, filter_txt='', filter_tag='', filter_prt_tag='', exact=False, results=None):
		"""
		Input an etree element and return that element filtering the tag, parent tag, and tag's associated text value
		- obj: Element tree object created from xml
		- filter_txt: gets objects that contain or match this text
		- filter_tag: gets objects that contain or match this tag
		- filter_prt_tag: gets objects that contain or match the parent tag
		- exact: False=filter string is in element value/tag, True=filter string exactly matches element value/tag
		- results: a list of filtered element objects. Only used for recursion not used outside that.
		
		return results: list of elements that match filter settings
		"""
	
        if results == None:
            results = []

        for v in obj.getchildren():
            v_str = '' if v.text == None else v.text.strip()
            t_str = v.tag.split('}')[-1] if '}' in v.tag else v.tag
            p_str = v.getparent().tag.split('}')[-1] if '}' in v.getparent().tag else v.getparent().tag
            if exact: # Filter is exact match
                if filter_txt.lower() == v_str.lower() and filter_tag.lower() == t_str.lower() and filter_prt_tag.lower() == p_str.lower():
                    results += [v]
            else: # Filter Contains key word
                if filter_txt.lower() in v_str.lower() and filter_tag.lower() in t_str.lower() and filter_prt_tag.lower() in p_str.lower():
                    results += [v]

            self._filter_etree(v, results=results, filter_txt=filter_txt, filter_tag=filter_tag, filter_prt_tag=filter_prt_tag, exact=exact)

        return results
    
    def get_action_arguments(self, action_name, arg_dir=None):
		"""
			- action_name: action that you would like all arguments for
			- arg_dir: None, 'in', 'out'
			
			return arguments associated with action name that are either inputs, outputs, or both depending on arg_dir
		"""
	
        action = self._filter_etree(self.service_root, filter_tag='name', filter_prt_tag='action', filter_txt=action_name)
        if len(action) == 0:
            return

        action = action[0].getparent()
        arguments = self._filter_etree(action, filter_prt_tag='argument', filter_tag='name')
        if arg_dir == None:
            return arguments

        # Get arguments only for specified direction
        filtered_args = []
        directions = self._filter_etree(action, filter_prt_tag='argument', filter_tag='direction')
        for a, d in zip(arguments, directions):
            if d.text == arg_dir:
                filtered_args += [a]

        return filtered_args
        
    def pretty_print_actions(self, name_filter='', show_datatype=False): 
        actionlist = self._filter_etree(self.service_root, filter_tag='actionlist')[0]
        actions = self._filter_etree(actionlist, filter_tag='action')
        for action in actions:
            name = self._filter_etree(action, filter_tag='name')[0].text
            if name_filter.lower() not in name.lower():
                continue

            arguments = self._filter_etree(action, filter_tag='argument', filter_prt_tag='argumentlist')

            print_str = name + '('
            in_args, out_args = [], []
            for arg in arguments:
                aname = self._filter_etree(arg, filter_tag='name', filter_prt_tag='argument')[0].text
                adir = self._filter_etree(arg, filter_tag='direction', filter_prt_tag='argument')[0].text

                desc_dict = self.get_statevar_desc(name, aname)
                dt = '[%s]'%(desc_dict['dataType']) if 'dataType' in desc_dict and show_datatype else ''

                if adir == 'in':
                    in_args += [aname + dt]
                elif adir == 'out':
                    out_args += [aname + dt]
            print_str += ', '.join(in_args) + ')'
            if len(out_args) > 0:
                print_str += '\r\n\tReturns: (%s)' % (', '.join(out_args)) 
            print(print_str)
            
    def get_relatedstatevariable(self, action_name, arg_name):
        action = self._filter_etree(self.service_root, filter_prt_tag='action', filter_tag='name', filter_txt=action_name)
        assert len(action) > 0, '(%s) action not found'%(action_name)
        action = action[0].getparent()
        argument = self._filter_etree(action, filter_prt_tag='argument', filter_tag='name', filter_txt=arg_name)
        assert len(argument) > 0, '(%s) argument not found'%(arg_name)
        argument = argument[0].getparent()
        return self._filter_etree(argument, filter_tag='relatedstatevariable')[0].text

    def get_statevar_desc(self, action_name, arg_name, show_id=False):
        rsv = self.get_relatedstatevariable(action_name, arg_name)
        statevar = self._filter_etree(self.service_root, filter_prt_tag='statevariable', filter_tag='name', filter_txt=rsv, exact=True)[0].getparent()

        tags = {}
        for sv_tag in statevar.getchildren():
            tg = sv_tag.tag
            if not(show_id) and 'name' in tg:
                continue

            if '}' in tg:
                tg = tg.split('}')[-1]

            if any([v in tg.lower() for v in ['list', 'range']]):
                arglist = []
                for item in sv_tag.getchildren():
                    arglist += [item.text]
                text = ', '.join(arglist)
            else:
                text = sv_tag.text
            tags[tg] = text

        return tags
    
    def _guess_arg_value(self, desc): 
        datatype = ''
        for k, v in desc.items():
            kl = k.lower()
            if k != '':
                if 'list' in kl and len(v.split(',')) == 1:
                    return v
                elif 'default' in kl:
                    if datatype in ['ui2', 'ui4', 'i2', 'i4']:
                        return int(v)
                    elif datatype in ['string', 'str']:
                        return str(v)
                    else:
                        return v
                elif 'datatype' in kl:
                    datatype = v
                    if v in ['ui2', 'ui4']:
                        return 0  
                elif 'range' in kl and len(v.split(',')) > 1:
                    try:
                        return int(v.split(',')[0])
                    except:
                        pass
        return None

    def define_action(self, action_name):
        self.action_name = action_name
        
        args = self.get_action_arguments(action_name, arg_dir='in')
        assert args != None, 'There was no (%s) action found.'%(action_name)

        arg_dict = {}
        for arg in args:
            desc = self.get_statevar_desc(action_name, arg.text)                    
            arg_dict[arg.text] = self._guess_arg_value(desc)

        self.input_args = arg_dict
        return arg_dict

    def print_action_arg_desc(self, action_name):
        for arg_dir in ['in', 'out']:
            print('_______%sput arguments________'%(arg_dir))
            args = self.get_action_arguments(action_name, arg_dir=arg_dir)
            assert args != None, 'There was no (%s) action found.'%(action_name)

            for arg in args:
                print(arg.text)
                desc = self.get_statevar_desc(action_name, arg.text)
                for k, v in desc.items():
                    if k != '':
                        print('\t%s: %s'%(k, v))
            print()
    
class UPNP_SOAP:
    SOAP_ENVELOPE = 'http://schemas.xmlsoap.org/soap/envelope'
    SOAP_ENCODING = 'http://schemas.xmlsoap.org/soap/encoding/'
    
    def __init__(self, ctrl_url, service_type, action_name, input_args):
        self.ctrl_url = ctrl_url
        self.service_type = service_type
        self.action_name = action_name
        
        if input_args == None:
            input_args = {}
        self.input_args = input_args
        
        self.soap_call()
    
    def create_soap_body(self, encoding='utf-8'):
        soap_env = '{%s}'%self.SOAP_ENVELOPE
        m = '{%s}'%self.service_type
        root = etree.Element(soap_env+'Envelope', nsmap={'SOAP-ENV': self.SOAP_ENVELOPE})
        root.attrib[soap_env+'encodingStyle'] = self.SOAP_ENCODING
        body = etree.SubElement(root, soap_env+'Body')

        action = etree.SubElement(body, m+self.action_name, nsmap={'m': self.service_type})
        for key, value in self.input_args.items():
            etree.SubElement(action, key).text = str(value)

        body = etree.tostring(root, encoding=encoding, xml_declaration=True)

        return body

    def soap_call(self):
        self.soap_body = self.create_soap_body()
        soap_action = "%s#%s"%(self.service_type, self.action_name)

        self.headers = {
            'SOAPAction': '"%s"'%(soap_action),
            'Host': '192.168.1.14:9197',
            'Content-Type': 'text/xml',
            'Content-Length': str(len(self.soap_body)),
        }

        response = requests.post(self.ctrl_url, self.soap_body, headers=self.headers)
        
        self.response = response.content.strip()
        return self.response
        
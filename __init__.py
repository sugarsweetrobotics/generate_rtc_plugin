import os, sys, types, re

import wasanbon
from wasanbon.core.plugins import PluginFunction, manifest
from idl_parser import parser

class PortProf:
    def __init__(self, parser, port):
        self.name = port.name
        self.varname = port['rtcExt:variableName']
        self._parser = parser
        self.constructor_code = self.create_constructor_code(port.type)


    def create_constructor_code(self, typeName):

        typs = self._parser.global_module.find_types(typeName)

        typ = typs[0]
        def type_to_code(t):
            code = ''
            if type(t) == types.StringType:
                code = t
            elif t.is_struct:
                code = code + t.full_path + '('
                for i, m in enumerate(t.members):
                    if m.type.is_primitive:
                        code = code + '0'
                    else:
                        code = code + type_to_code(m.type)
                    if i != len(t.members)-1:
                        code = code + ', '
                code = code + ')'
            
            elif t.is_typedef:
                code = '<' + t.full_path + '>'
            else:
                code = t.full_path

            return code 

        code = type_to_code(typ)
        code = re.sub(r'::', r'.', code)
        return code
        


class Plugin(PluginFunction):
    """ This plugin gives the function for generating RTC skeleton code from RTC.xml (RTC Profile) """

    def __init__(self):

        super(Plugin, self).__init__()
        pass

    def depends(self):
        return ['admin.environment', 'admin.package', 'admin.rtc']

    def _print_alternatives(self, args):
        print 'hoo'
        print 'foo'
        print 'hoge'
        print 'yah'

    def search_idls(self, path, except_files=[]):
        idls = []
        include_dirs = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.idl') and not (os.path.basename(file) in except_files):
                    idls.append(os.path.join(root, file))
                    if root not in include_dirs:
                        include_dirs.append(root)
        
        return (idls, include_dirs)

    @manifest
    def generate(self, argv):
        """ Generate RTC skeleton code.
         # Usage: mgr.py generate_rtc generate [RTC_NAME]
        """
        self.parser.add_option('-f', '--force', help='Force option (default=False)', default=False, action='store_true', dest='force_flag')
        options, argv = self.parse_args(argv[:], self._print_alternatives)
        verbose = options.verbose_flag # This is default option
        force   = options.force_flag

        wasanbon.arg_check(argv, 4)

        rtm_root_path = wasanbon.get_rtm_root()
        default_idl_path = os.path.join(rtm_root_path, 'rtm')
        except_files = ['SDOPackage.idl', 'Manager.idl', 'OpenRTM.idl', 'RTC.idl'] 
        idls, idl_dirs = self.search_idls(default_idl_path, except_files=except_files)
        
        idls = [os.path.join(default_idl_path, 'idl', 'BasicDataType.idl'),
                os.path.join(default_idl_path, 'idl', 'ExtendedDataTypes.idl'),
                os.path.join(default_idl_path, 'idl', 'InterfaceDataTypes.idl')]
        
        self._parser = parser.IDLParser(verbose=verbose)
        self._parser.parse(idls=idls, idl_dirs = idl_dirs, except_files=except_files)


        pack = admin.package.get_package_from_path(os.getcwd())
        rtc = admin.rtc.get_rtc_from_package(pack, argv[3], verbose=verbose)

        self.generate_codes_from_profile(rtc)


    def get_outports(self, rtcprof):
        ports = []

        for d in rtcprof.dataports:
            if d.portType == 'DataOutPort':
                ports.append(PortProf(self._parser, d))
        return ports

    def get_inports(self, rtcprof):
        return []

    def generate_codes_from_profile(self, rtc):
        code = self.generate_code_from_profile(rtc.rtcprofile)
        with open(os.path.join(rtc.path, rtc.rtcprofile.basicInfo.name + '.py'), 'w') as f:
            f.write(code)
            pass

    def generate_code_from_profile(self, rtcprof):
        template_dir = os.path.join(__path__[0], 'template')
        code = ''
        from jinja2 import Template
        with open(os.path.join(template_dir,'python', 'rtc_py.py'), 'r') as pyfile:
            template = Template(pyfile.read())
            code = template.render(rtcprofile=rtcprof, outports=self.get_outports(rtcprof), inports=self.get_inports(rtcprof))
        return code



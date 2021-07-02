import json
import os
import time
from os import listdir, path
from shutil import copyfile

import requests


class SonarNovobi():

    def __init__(self):
        super().__init__()

        self.host_url = 'http://localhost:9000'

        # Server dir
        self.server_quality_dir = './novobi_data'
        self.server_quality_profiles_dir = path.join(
            self.server_quality_dir, 'quality_profiles')
        self.server_quality_gates_json = path.join(
            self.server_quality_dir, 'quality_gates.json')

        # Local dir
        self.local_quality_dir = '/opt/sonarqube/data/local_data'
        self.local_quality_gates_json = path.join(
            self.local_quality_dir, 'quality_gates.json')
        self.local_quality_profiles_dir = path.join(
            self.local_quality_dir, 'quality_profiles')

        self.server_quality_profile_language = ['cs', 'css', 'flex', 'go', 'java', 'js',
                                                'jsp', 'kotlin', 'php', 'py', 'ruby', 'scala', 'ts', 'vbnet', 'web', 'xml']

    def create_local_data(self):
        try:
            os.makedirs(self.local_quality_profiles_dir, mode=0o755)
        except OSError:
            pass

    def load_local_data(self):
        if path.isfile(self.local_quality_gates_json):
            with open(self.local_quality_gates_json, 'r') as f:
                self.local_data = json.load(f)
            f.close()
            self.local_quality_gates_list = self.local_data['qualitygates']
            return True
        else:
            self.create_local_data()
            return False

    def load_server_data(self):
        if path.isfile(self.server_quality_gates_json):
            with open(self.server_quality_gates_json, 'r') as f:
                self.data = json.load(f)
            f.close()
            self.server_quality_gates_list = self.data['qualitygates']
            return True
        else:
            print('Error: server_quality_gates.json is not exist!')
            return False

    def create_quality_profile(self, language, name):
        url = self.host_url + '/api/qualityprofiles/create?'
        language = '&language=' + language
        name = '&name=' + name
        api_url = url + language + name
        self.send_api_request(api_url, 'post')

    def create_ignored_quality_profiles(self):
        if not self.search_quality_profile('py', 'Ignored'):
            for language in self.server_quality_profile_language:
                self.create_quality_profile(language, 'Ignored')
                self.set_default_quality_profile(language, 'Ignored')

    def set_default_quality_profile(self, language, name):
        url = self.host_url + '/api/qualityprofiles/set_default?'
        language = '&language=' + language
        quality_profile = '&qualityProfile=' + name.replace(' ', '%20')
        api_url = url + language + quality_profile
        self.send_api_request(api_url, 'post')

    def search_quality_profile(self, language, name):
        url = self.host_url + '/api/qualityprofiles/search?'
        language = '&language=' + language
        name = '&qualityProfile=' + name
        api_url = url + language + name
        response = self.send_api_request(api_url, 'get').json()
        return response['profiles']

    def update_quality_profiles(self):
        print('Updating quality profiles...')
        self.create_ignored_quality_profiles()
        api_url = self.host_url + '/api/qualityprofiles/restore'
        quality_profile_files = [f for f in listdir(
            self.server_quality_profiles_dir) if path.isfile(path.join(self.server_quality_profiles_dir, f))]
        for quality_profile in quality_profile_files:
            file_path = path.join(
                self.server_quality_profiles_dir, quality_profile)
            files = [
                ('backup', (quality_profile, open(file_path, 'rb'), 'text/xml'))]
            self.send_api_request(api_url, 'post', files=files)
        self.set_default_quality_profile('py', 'Novobi way')

    def get_quality_gates_name(self,):
        api_url = self.host_url + '/api/qualitygates/list'
        current_quality_gates_list = self.send_api_request(
            api_url, 'get').json()
        self.current_quality_gates_name = []
        for quality_gate in current_quality_gates_list['qualitygates']:
            name = quality_gate['name']
            self.current_quality_gates_name.append(name)
        self.current_quality_gates_name.remove('Sonar way')

    def create_quality_gate(self, name):
        url = self.host_url + '/api/qualitygates/create?name='
        api_url = url + name.replace(' ', '%20')
        self.send_api_request(api_url, 'post')

    def delete_quality_gate(self, name):
        url = self.host_url + '/api/qualitygates/destroy?name='
        api_url = url + name.replace(' ', '%20')
        self.send_api_request(api_url, 'post')

    def reset_quality_gate(self, name):
        self.delete_quality_gate(name)
        self.create_quality_gate(name)

    def create_quality_gate_conditions(self, name, conditions):
        url = self.host_url + '/api/qualitygates/create_condition?'
        gate_name = '&gateName=' + name.replace(' ', '%20')
        for condition in conditions:
            metric = '&metric=' + condition['metric']
            op = '&op=' + condition['op']
            error = '&error=' + condition['error']
            api_url = url + gate_name + metric + op + error
            self.send_api_request(api_url, 'post')

    def set_default_quality_gate(self, name):
        url = self.host_url + '/api/qualitygates/set_as_default?name='
        api_url = url + name.replace(' ', '%20')
        self.send_api_request(api_url, 'post')

    def update_quality_gates(self):
        self.get_quality_gates_name()
        self.set_default_quality_gate('Sonar way')
        for quality_gate in self.server_quality_gates_list:
            name = quality_gate['name']
            print('Updating quality gate: ' + name)
            conditions = quality_gate['conditions']
            is_default = quality_gate['isDefault']
            if is_default:
                self.current_default_quality_gate = name
            if name in self.current_quality_gates_name:
                self.reset_quality_gate(name)
            else:
                self.create_quality_gate(name)
            self.create_quality_gate_conditions(name, conditions)
        self.set_default_quality_gate(self.current_default_quality_gate)

    # def check_user_token(self, name):
    #     url = self.host_url + '/api/user_tokens/search?login='
    #     api_url = url + name
    #     response = self.send_api_request(api_url, 'get').json()
    #     return response['userTokens']

    # def generate_user_token(self, name):
    #     url = self.host_url + '/api/user_tokens/generate?login=admin'
    #     token_name = '&name=' + name
    #     api_url = url + token_name
    #     response = self.send_api_request(api_url, 'post').json()
    #     return response['token']

    # def replace_user_token(self, token):
    #     if path.isfile(self.server_quality_gates_json):
    #         with open(self.sonar_scanner_file) as f:
    #             add_token = f.read().replace('admin_token', token)
    #         with open(self.sonar_scanner_file, "w") as f:
    #             f.write(add_token)
    #     else:
    #         print(
    #             'Error: docker-compose.yml is not exist! Can not set up admin user token!')

    # def set_up_user_token(self):
    #     if not self.check_user_token('admin'):
    #         print('Setting up admin user token...')
    #         print('------------------------------')
    #         token = self.generate_user_token('admin')
    #         print('Your admin user token is: ' + token)
    #         print('------------------------------')
    #         self.replace_user_token(token)

    def send_api_request(self, api_url, request_type, headers={"Authorization": "Basic YWRtaW46YWRtaW4="}, data={}, files=[]):
        try:
            if request_type == 'post':
                response = requests.post(
                    api_url, headers=headers, data=data, files=files)
            elif request_type == 'get':
                response = requests.get(api_url, headers=headers)
            return response
        except requests.ConnectionError as e:
            print('Connection Error: ', e)
            raise SystemExit(0)

    def check_sonar_host(self):
        url = self.host_url + '/api/system/status'
        try:
            response = requests.get(
                url, headers={"Authorization": "Basic YWRtaW46YWRtaW4="}).json()
            if response['status'] != 'UP':
                return 0
        except requests.ConnectionError:
            return 0
        return 1

    def compare_quality_gates(self):
        if path.isfile(self.local_quality_gates_json):
            server_quality_gates = json.dumps(
                self.server_quality_gates_list, sort_keys=True)
            local_quality_gates = json.dumps(
                self.local_quality_gates_list, sort_keys=True)
            if server_quality_gates != local_quality_gates:
                self.update_quality_gates()
                copyfile(self.server_quality_gates_json,
                         self.local_quality_gates_json)
        else:
            self.update_quality_gates()
            copyfile(self.server_quality_gates_json,
                     self.local_quality_gates_json)

    def compare_quality_profiles(self):
        server_quality_profile_files = [f for f in listdir(
            self.server_quality_profiles_dir) if path.isfile(path.join(self.server_quality_profiles_dir, f))]
        for quality_profile in server_quality_profile_files:
            server_file_path = path.join(
                self.server_quality_profiles_dir, quality_profile)
            local_file_path = path.join(
                self.local_quality_profiles_dir, quality_profile)

            if path.isfile(local_file_path):
                with open(server_file_path, 'r') as f:
                    server_quality_profile = f.read()
                f.close()

                with open(local_file_path, 'r') as f:
                    local_quality_profile = f.read()
                f.close()

                if server_quality_profile != local_quality_profile:
                    self.update_quality_profiles()
                    copyfile(server_file_path, local_file_path)
            else:
                self.update_quality_profiles()
                copyfile(server_file_path, local_file_path)

    def compare_data(self):
        if self.load_server_data():
            self.load_local_data()
            self.compare_quality_profiles()
            self.compare_quality_gates()

    def update_data(self):
        time.sleep(40)
        while True:
            check_host = self.check_sonar_host()
            if check_host:
                self.compare_data()
                break
            else:
                time.sleep(5)


if __name__ == '__main__':
    sonar = SonarNovobi()
    sonar.update_data()

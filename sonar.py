#!/usr/bin/env python3

import os
import time
import re
import argparse

DOCKER_COMPOSE = 'docker compose'
DOCKER = 'docker'
WORK_DIR = '/opt/odoo'
SCAN_DIR = WORK_DIR + '/customized_addons'
COVERAGE_REPORT = WORK_DIR + '/coverage.xml'
JUNIT_REPORT = WORK_DIR + '/junit.xml'
MODULES_FILE = 'unit-test-modules.txt'


def scan_code(work_dir, scan_dir, project_key, coverage_report=None, junit_report=None):
    cmd = [DOCKER]
    cmd.append('run --rm -it --network host')
    volume = {
        os.getcwd(): work_dir
    }
    environment = {
        'SONAR_PROJECT_BASE_DIR': scan_dir,
        'SONAR_COVERAGE_REPORT': coverage_report,
        'SONAR_XUNIT_REPORT': junit_report
    }
    for key, value in volume.items():
        if value:
            cmd.append('-v {}:{}'.format(key, value))
    for key, value in environment.items():
        if value:
            cmd.append('-e {}={}'.format(key, value))
    cmd.append('novobidevops/sonar-scanner')
    cmd.append(project_key)
    return os.system(' '.join(cmd))


def parse_test_modules(file_path):
    with open(file_path, 'r') as file:
        txt = file.read()
        txt = re.sub(r'#.*', '', txt)
        txt = re.sub(r'^\s*', '', txt)
        modules = txt.split('\n')
        modules = list(map(lambda module: module.strip(), modules))
        return modules


def start_postgresql():
    return os.system(
        '{docker_compose} -p unit-test run --rm -dit --name unit-test_postgres --use-aliases --no-deps postgres'.format(docker_compose=DOCKER_COMPOSE))


def wait_for_postgresql():
    while os.system('{docker_compose} -p unit-test exec -it postgres pg_isready'.format(docker_compose=DOCKER_COMPOSE)):
        print('Waiting for postgresql server start...')
        time.sleep(2)


def run_unit_test(modules, work_dir):

    return os.system('{docker_compose} -p unit-test run --rm -it -w {work_dir} --no-deps odoo \
        bash -c "{work_dir}/odoo/odoo-bin -c {work_dir}/odoo.conf --log-level=test -d unit-test-db --stop-after-init -i {modules_comma} \
            && pip3 install pytest pytest-odoo pytest-cov \
            && cd {work_dir}/odoo \
            && python3 setup.py install \
            && cd {scan_dir} \
            && pytest --odoo-config={work_dir}/odoo.conf --odoo-database=unit-test-db --odoo-log-level=test --junit-xml={work_dir}/junit.xml --disable-pytest-warnings --cov-report=xml:{work_dir}/coverage.xml --cov={scan_dir} --cov-branch --rootdir={scan_dir} {modules_dir}"'.format(docker_compose=DOCKER_COMPOSE, modules_comma=','.join(modules), work_dir=work_dir, modules_dir=' '.join(modules), scan_dir=SCAN_DIR))


def clean():
    os.system('{docker} kill unit-test_postgres'.format(docker=DOCKER))
    os.system(
        '{docker_compose} -p unit-test down -v'.format(docker_compose=DOCKER_COMPOSE))


def main():
    parser = argparse.ArgumentParser(description='Run code analysis')
    parser.add_argument(
        '--project-key', default='sonarqube-local', help='Your project key')
    parser.add_argument('--unit-test', '-t', action='store_true',
                        help='Analyze code with unit test')
    parser.add_argument(
        '--postgres-version', help='PostgreSQL version to run unit test [Default: 14]', default='14')

    args = vars(parser.parse_args())
    project_key = args['project_key']
    os.environ['POSTGRES_VERSION'] = args['postgres_version']

    if args['unit_test']:
        start_postgresql()
        wait_for_postgresql()
        run_unit_test(parse_test_modules(MODULES_FILE), WORK_DIR)
        clean()
        scan_code(WORK_DIR, SCAN_DIR, project_key,
                  COVERAGE_REPORT, JUNIT_REPORT)
    else:
        scan_code(WORK_DIR, SCAN_DIR, project_key)


if __name__ == "__main__":
    main()

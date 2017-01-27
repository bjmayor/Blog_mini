#!/usr/bin/env python3
# _*_ coding: utf-8 _*_

'''
Deployment toolkit. for blog.go2live.cn python2.x
fab build
fab deploy
fab rollback
fab backup
fab restore2local
'''

import os, re

from datetime import datetime
from fabric.api import *

#服务器配置
env.user = 'work'
env.sudo_user = 'root'
env.hosts=['123.57.145.149']

#数据库配置
db_user = 'root'
db_password = ''
db_host = 'localhost'

#发布设置
_TAR_FILE = 'blog.go2live.cn.tar.gz'
_REMOTE_TMP_TAR = '/tmp/%s' % _TAR_FILE
#服务器代码目录
_REMOTE_BASE_DIR = '/data/www/blog'

def _current_path():
    return os.path.abspath('.')

def _now():
    return datetime.now().strftime('%y-%m-%d_%H.%M.%S')

def backup():
    '''
    把服务器的数据库导出来并备份到本地.
    :return:
    '''
    dt = _now()
    f = 'backup-blog-%s.sql' % dt
    with cd('/tmp'):
        run('mysqldump --user=%s --password=%s --host=%s --skip-opt --add-drop-table --default-character-set=utf8 --quick blog> %s' % (db_user, db_password, db_host,f))
        run('tar -czvf %s.tar.gz %s' % (f,f))
        get('%s.tar.gz' % f, '%s/backup/' % _current_path())
        run('rm -f %s' % f)
        run('rm -f %s.tar.gz' % f)

def build():
    '''
    打包.把需要运行的代码弄出来的.包括static,templates,*.py文件
    :return:
    '''
    includes = ['app','*.py','requirements','tests']
    excludes = ['test', '.*','*.pyc','*.pyo']
    local('rm -f dist/%s' % _TAR_FILE)
    with lcd(os.path.join(_current_path(),'')):
        cmd = ['tar', '--dereference', '-czvf','dist/%s' % _TAR_FILE]
        cmd.extend(['--exclude=\'%s\'' % ex for ex in excludes])
        cmd.extend(includes)
        local(' '.join(cmd))

def deploy():
    newdir = 'www-%s' % _now()
    run('rm -f %s' % _REMOTE_TMP_TAR)
    put('dist/%s' % _TAR_FILE, _REMOTE_TMP_TAR)
    with cd(_REMOTE_BASE_DIR):
        sudo('mkdir -p %s' % newdir)
    with cd('%s/%s' % (_REMOTE_BASE_DIR, newdir)):
        sudo('tar -xzvf %s' % _REMOTE_TMP_TAR)
    with cd(_REMOTE_BASE_DIR):
        sudo('rm -f www')
        sudo('ln -s %s www' % newdir)
        sudo('chown work:work www')
        sudo('chown -R work:work %s' % newdir)
    #启动服务器.需要事先在服务器上配置好.
    with settings(warn_only=True):
        sudo('supervisorctl stop blog')
        sudo('supervisorctl start blog')
        sudo('service nginx restart')

RE_FILES = re.compile('\r?\n')

def rollback():
    '''
    回滚到上个版本
    :return:
    '''
    with cd(_REMOTE_BASE_DIR):
        r = run('ls -p -1')
        files = [s[:-1] for s in RE_FILES.split(r) if s.startswith('www-') and s.endswith('/')]
        files.sort(cmp=lambda s1,s2:1 if s1<s2 else -1)
        r = run('ls -l www')
        ss = r.split(' -> ')
        if len(ss) !=2:
            print('ERROR: \'www\' is not a symbol link.')
            return
        current = ss[1]
        print('Found current symbol link points to: %s\n' % current)
        try:
            index = files.index(current)
        except ValueError as e:
            print('ERROR:symbol link is invalid.')
            return
        if len(files) == index+1:
            print('ERROR: already the oldest version.')
        old = files[index+1]
        print('=================================================================')
        for f in files:
            if f == current:
                print('   Current ---> %s' % current)
            elif f == old:
                print('    Rollback to ---> %s' % old)
            else:
                print('                  %' % f)

        print('=================================================================')
        print('')
        yn = input('continue? y/N ')
        if yn !='y' and yn!='Y':
            print('Rollback cancelled.')
            return
        print('Start rollback...')
        sudo( 'rm -f www')
        sudo( 'ln -s %s www' % old)
        sudo('chown work:work www')
        with settings(warn_only=True):
            sudo('supervisorctl stop blog')
            sudo('supervisorctl start blog')
            sudo('service nginx restart')
        print('ROLLBACKED OK.')

def restore2local():
    '''
    回滚服务器的数据为本地的
    :return:
    '''
    backup_dir = os.path.join((_current_path(), 'backup'))
    fs = os.listdir(backup_dir)
    files = [f for f in fs if f.startswith('backup-') and f.endswith('.sql.tar.gz')]
    files.sort(cmp=lambda  s1,s2:1 if s1<s2 else -1)
    if len(files)==0:
        print('No backup files found.')
        return
    print('Found %s backup files:' % len(files))
    print('=================================================================')
    n = 0
    for f in files:
        print('%s: %s' % (n, f))
        n = n + 1
    print('=================================================================')
    print('')
    try:
        num = int(input('Restore file: '))
    except ValueError:
        print('Invalid file number.')
        return
    restore_file = files[num]
    yn = input('Restore file %s: %s? y/N' % (num, restore_file))
    if yn != 'y' and yn!='Y':
        print('Restore cancelled.')
        return
    print('Start restore to local database...')
    p = input('Input mysql root password: ')
    sqls = [
        'drop database if exists blog;',
        'create database blog;',
        'grant select, insert, update, delete on blog.* to \'%s\'@\'localhost\' identified by \'%s\';' % (db_user, db_password)
    ]
    for sql in sqls:
        local(r'mysql -uroot -p%s -e "%s"' % (p, sql))
    with lcd(backup_dir):
        local('tar zxvf %s' % restore_file)
    local(r'mysql -uroot -p%s blog< backup/%s' % (p, restore_file[:-7]))
    with lcd(backup_dir):
        local('rm -f %s' % restore_file[:-7])



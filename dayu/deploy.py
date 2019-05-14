from fabric import Connection
from time import sleep
from ding import dingding
import os, shutil
import zipfile
from datetime import datetime
from setting import VNPY_BRANCH, VNPY_UPGRADE, SERVERS, USER_HOME, working_path
from write_settings import assign_settings

class ding_content(object):
    def __init__(self):
        self.msg = "### 策略部署反馈\n\n"

    def send(self):
        dingding("Strategy Deployment",self.msg)

def pre_tasks():
    if os.path.exists(f"{working_path}/tmp"):
        shutil.rmtree(f"{working_path}/tmp")
        sleep(1)
    os.mkdir(f"{working_path}/tmp")
    sleep(1)
    
def install_vnpy(c, server_name, ding):
    with c.cd(f"{USER_HOME}/Documents/vnpy_fxdayu"):
        c.run(f"yes | {USER_HOME}/anaconda3/bin/pip uninstall vnpy_fxdayu")
        c.run(f"git pull origin {VNPY_BRANCH}")
        c.run(f"git checkout {VNPY_BRANCH}")
        
        c.run(f"{USER_HOME}/anaconda3/bin/python -E setup.py install")
        cmd_rtn = c.run("git reflog")
        ref_tag = cmd_rtn.stdout.split("\n")[0].split(" ")[0]
        ding.msg += f"> 服务器 {server_name} 已经更新到了 {VNPY_BRANCH} 分支的 {ref_tag} 版本 \n\n"

def zip_folder(startdir, file_news):
    file_name_list = []
    z = zipfile.ZipFile(file_news, 'w', zipfile.ZIP_DEFLATED) # 参数一：文件夹名
    for dirpath, dirnames, filenames in os.walk(startdir):
        fpath = dirpath.replace(startdir, '') # 这一句很重要，不replace的话，就从根目录开始复制
        fpath = fpath and fpath + os.sep or '' # 实现当前文件夹以及包含的所有文件的压缩
        for filename in filenames:
            z.write(os.path.join(dirpath, filename), fpath + filename)
        print(f'{dirpath}, 压缩成功')
        file_name_list.append(dirnames)
    return file_name_list[0]
    
def cp_files(c, server_name, ding):
    stg_path = f"{working_path}/push/{server_name}"
    new_stg_list = []
    zip_path = f"{working_path}/tmp/{server_name}.zip"
    new_stg_list = zip_folder(stg_path, zip_path)

    # c.local(f"tar -czvf {zip_path} {stg_path}") # Linux
    c.put(zip_path)
    # clean_target_strategy
    target_folder = f"{USER_HOME}/Strategy"
    c.run(f"rm -r {USER_HOME}/BACKUP")
    c.run(f"mkdir {USER_HOME}/BACKUP")
    with c.cd(target_folder):
        # move existing stg to backup folder
        #for stg in new_stg_list:
        #    if not stg:
        #        continue
        #    c.run(f"mv {stg} {USER_HOME}/BACKUP")
        #    print("move",stg)
        # depress strategy
        c.run(f"unzip {USER_HOME}/{server_name}.zip -d {target_folder}")
        # 获取解压出来的策略名
        t = c.run("ls")
        stg_list = t.stdout.split('\n')
        ding.msg += f" - 策略 {stg_list} 成功推送到了服务器 {server_name} \n\n"
    # 清理
    c.run(f"rm {USER_HOME}/{server_name}.zip")
    
def run_strategy(c):
    with c.cd(f"{USER_HOME}/Strategy"):
        cmd_rtn = c.run("ls")
        """
        stdout 输出
        # {'stdout': 'adxDiEosStrategy\nhlBreakEosStrategy\nStrategy_eos_macd\n', 
        # 'stderr': '', 'encoding': 'cp936', 'command': 'cd /home/dayu/LTS190404 && ls', 
        # 'shell': 'C:\\Windows\\system32\\cmd.exe', 'env': {}, 'exited': 0, 'pty': False, 
        # 'hide': (), 'connection': <Connection host=149.248.20.149 user=dayu>}
        """
        stg_list = cmd_rtn.stdout.split("\n")
        i=1
        for stg in stg_list:
            if not stg:
                continue
            with c.cd(f"{USER_HOME}/Strategy/{stg}"):
                if i%2 ==0:
                    sleep(60)
                # cmd_rtn = c.run(f"nohup {USER_HOME}/anaconda3/bin/python runCtaTrading.py &")
                cmd_rtn = c.run(f"nohup {USER_HOME}/anaconda3/bin/vnpy run terminal -m &")
                print(cmd_rtn.__dict__)
                i+=1

def main():
    pre_tasks()
    ding = ding_content()
    updating_machine_list = assign_settings(ding)
    updating_machine_list=["DAYU02","DAYU01"]
    for server_name in list(set(updating_machine_list)):
        print(server_name)
        c = Connection(f"dayu@{SERVERS[server_name]}", connect_kwargs = {"password":"Xinger520"})
        if VNPY_UPGRADE:
            install_vnpy(c, server_name, ding)
        cp_files(c, server_name, ding)
        #run_strategy(c, ding)
    ding.send()

if __name__=="__main__":
    main()
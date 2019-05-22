import os,json,shutil
import pandas as pd
from config import USER_HOME, source_folder, working_path
from datetime import datetime 
import git
import random
import zipfile

def update_repo():
    repo = git.cmd.Git(source_folder)
    repo.pull()
    a = repo.reflog()
    return f" - 策略代码更新至版本号: {a.split(' ')[0]} \n"

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

def cp_files(c, server_name, task_id):
    stg_path = f"{working_path}/{task_id}/{server_name}"
    new_stg_list = zip_folder(stg_path, f"{stg_path}.zip")

    # c.local(f"tar -czvf {zip_path} {stg_path}") # Linux
    c.put(f"{stg_path}.zip")

    # clean_target_strategy
    target_folder = f"{USER_HOME}/Strategy"
    c.run(f"rm -r {USER_HOME}/BACKUP")
    c.run(f"mkdir {USER_HOME}/BACKUP")
    with c.cd(target_folder):
        # move existing stg to backup folder
        for stg in new_stg_list:
            if not stg:
                continue
            try:
                c.run(f"mv {stg} {USER_HOME}/BACKUP")
                print("moved:",stg)
            except:
                print("no exists: ",stg)

        # depress strategy
        c.run(f"unzip {USER_HOME}/{server_name}.zip -d {target_folder}")
        # 获取解压出来的策略名
        t = c.run("ls")
        stg_list = t.stdout.split('\n')
    # 清理
    c.run(f"rm {USER_HOME}/{server_name}.zip")

    update_list = set(new_stg_list) &set(stg_list)
    return f" - 策略 {update_list} 成功推送到了服务器 {server_name} \n\n"
    
    
def prepare_stg_files(data,task_id,key_chain):
    s = f"{working_path}/{task_id}"
    if os.path.exists(s):
        shutil.rmtree(s)

    for stg in data:
        working_folder = f"{working_path}/{task_id}/{stg['server']}/{stg['name']}"
        # 复制工作目录
        shutil.copytree(f"{source_folder}/{stg['git_path']}",f"{working_folder}")
        # 复制运行脚本
        shutil.copyfile(f"{source_folder}/RS_setting.json",f"{working_folder}/RS_setting.json")
        
        # 生成cta setting
        with open(f"{working_folder}/CTA_setting.json","w") as f:
            # 直接覆盖，不读取
            setting = stg["strategy_setting"]
            setting["name"] = stg["name"]
            setting["className"] = stg["strategy_class_name"]
            setting["symbolList"] = stg["symbolList"]
            setting["tradingSymbolList"] = stg["tradeSymbolList"]
            setting["STATUS_NOTIFY_PERIOD"] = 3600
            setting["STATUS_NOTIFY_SHIFT"] = 60 * random.randint(1,40)
            setting["ENABLE_STATUS_NOTICE"] = True
            setting["author"] = stg["Author"]

            json.dump([setting], f, indent = 4)

        # 生成connect
        key_list = list(set(stg['trade_symbols_ac'] + stg['assist_symbols_ac']))
        for ac in key_list:
            with open(f"{working_folder}/OKEX_{ac}_connect.json","w") as f:
                setting = {
                    "apiKey": key_chain[ac][0],
                    "apiSecret": key_chain[ac][1],
                    "passphrase": key_chain[ac][2],
                    "symbols": list(map(lambda x: x.split(":")[0], stg["symbolList"])),
                    "future_leverage": 20,
                    "swap_leverage": 100,
                    "margin_token": 0,
                    "sessionCount": 3,
                    "setQryEnabled": True,
                    "setQryFreq": 60,
                    "trace": False,
                }
                json.dump(setting, f, indent = 4)
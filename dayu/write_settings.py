import os,json,shutil
import pandas as pd
from setting import stg_folder, apikey_path, working_path, excel_path, excel_name, sheet_name
from datetime import datetime 
import git
import random

def read_settings():
    data = pd.read_excel(f"{excel_path}/{excel_name}",sheet_name = sheet_name)
    data = data[["Type","Name","Machine","Key","SymbolList","Param","Author","tradingSymbolList","LTS_Key","LTS_Param"]]
    data.dropna(how='all',inplace = True)

    os.mkdir(f"{working_path}/push")

    return data

def update_repo(ding):
    repo = git.cmd.Git(stg_folder)
    repo.pull()
    a = repo.reflog()
    ding.msg += f" - 策略代码更新至版本号: {a.split(' ')[0]} \n\n"
    ding.msg += f"{datetime.now().strftime('%Y%m%d %H:%M:%S')}\n\n"

def copy_to_workingfolder(stg_type, name, apikey, working_folder):
    shutil.copytree(f"{stg_folder}/{stg_type}/{name}",f"{working_folder}")
    #复制密钥
    shutil.copyfile(f"{apikey_path}/OKEX_{apikey}_connect.json",f"{working_folder}/OKEX_{apikey}_connect.json")
    #复制运行脚本
    shutil.copyfile(f"{stg_folder}/RS_setting.json",f"{working_folder}/RS_setting.json")

def modify_key_setting(working_folder, apikey, symbolList):
    with open(f"{working_folder}/OKEX_{apikey}_connect.json") as f:
        settings = json.load(f)
        settings["symbols"] = symbolList
    with open(f"{working_folder}/OKEX_{apikey}_connect.json", "w") as f:    
        json.dump(settings, f, indent = 4)

def modify_cta_setting(working_folder, name, param, vtSymbols, author,trading, is_LTS = False):
    with open(f"{working_folder}/CTA_setting.json") as f:
        settings = json.load(f)
        for idx, setting in enumerate(settings):
            if "className" not in setting.keys():
                setting['className'] = setting['classname']

            setting["name"] = f"{name.replace('Strategy','')}"
            if is_LTS:
                setting["name"] = f"LTS{setting['name']}"
            setting["symbolList"] = vtSymbols

            if not pd.isnull(param):
                setting["tradingSymbolList"] = trading
            else:
                setting["tradingSymbolList"] = vtSymbols

            setting["STATUS_NOTIFY_PERIOD"] = 3600
            setting["STATUS_NOTIFY_SHIFT"] = 60 * random.randint(1,40)
            setting["ENABLE_STATUS_NOTICE"] = True
            setting["author"] = author
            
            if not pd.isnull(param):
                param_list = param.split(",")

                for param in param_list:
                    p, v = param.replace(" ","").split(":")
                    setting[p] = eval(v)
            
            settings[idx] = setting

    with open(f"{working_folder}/CTA_setting.json","w") as f:
        json.dump(settings, f, indent = 4)

def assign_settings(ding):
    # clear working path
    if os.path.exists(f"{working_path}/push"):
        shutil.rmtree(f"{working_path}/push")

    # 按策略读写配置
    data = read_settings()
    update_repo(ding)
    updating_machine = []
    for idx, row in data.iterrows():
        stg_type, name, machine, apikey, symbols, param, author, trading, LTS_key, LTS_param = row.values
        symbolList = symbols.replace(" ","").split(",")

        # 复制策略文件夹到工作路径
        working_folder = f"{working_path}/push/{machine}/{name}"
        copy_to_workingfolder(stg_type, name, apikey, working_folder)

        # 合成交易标的
        vtSymbols = []
        for symbol in symbolList:
            vtSymbols.append(f"{symbol}:OKEX_{apikey}")
        tradingsym = []
        if not pd.isnull(trading):
            trading_ = trading.replace(" ","").split(",")
            for symbol in trading_:
                tradingsym.append(f"{symbol}:OKEX_{apikey}")
        else:
            tradingsym = vtSymbols
        # 修改密钥订阅
        modify_key_setting(working_folder, apikey, symbolList)
        # 修改cta_setting
        modify_cta_setting(working_folder, name, param, vtSymbols, author, tradingsym)

        # LTS 归集
        if not pd.isnull(LTS_key):
            working_folder = f"{working_path}/push/DAYU01/{name}"
            copy_to_workingfolder(stg_type, name, LTS_key, working_folder)

            vtSymbols = []
            for symbol in symbolList:
                vtSymbols.append(f"{symbol}:OKEX_{LTS_key}")

            tradingsym = []
            if not pd.isnull(trading):
                trading_ = trading.replace(" ","").split(",")
                for symbol in trading_:
                    tradingsym.append(f"{symbol}:OKEX_{LTS_key}")
            else:
                tradingsym = vtSymbols

            # 修改密钥订阅
            modify_key_setting(working_folder, LTS_key, symbolList)
            # 修改cta_setting
            modify_cta_setting(working_folder, name, LTS_param, vtSymbols, author,tradingsym,is_LTS = True)

            updating_machine.append("DAYU01")

        updating_machine.append(machine)
    return updating_machine
            
    # 删除下载的excel
    shutil.copyfile(f"{excel_path}/{excel_name}", f"{working_path}/push/{excel_name}")
    os.remove(f"{excel_path}/{excel_name}")
"""
Provide product price of each customer
"""
from datetime import datetime,timezone,timedelta
from flask import make_response, abort,request
from sqlalchemy import create_engine
import requests
import json
import random
import psycopg2
import pandas as pd
import os
import logging
import time
logging.basicConfig(level=logging.INFO,format='[%(asctime)s] [%(process)s] [%(levelname)s] [%(funcName)s] %(message)s')


engine = create_engine('postgresql+psycopg2://{username}:{password}@{host}/{dbname}'.format(username = os.environ['posuser']
                                                                                        , password = os.environ['pospwd']
                                                                                        , host = os.environ['poshost']
                                                                                        , dbname = os.environ['posdb']), pool_recycle = int(os.environ['posport']), echo = False, encoding = 'utf-8')
def connectDB():
    return psycopg2.connect(database=os.environ['posdb'], user=os.environ['posuser'], password=os.environ['pospwd'], host=os.environ['poshost'], port=os.environ['posport'])


def get_timestamp(format_type):
    if format_type == 'TXNSEQ':
        return datetime.now().astimezone(timezone(timedelta(hours=8))).strftime(("%Y%m%d%H%M%S"))
    else:
        return datetime.now().astimezone(timezone(timedelta(hours=8))).strftime(("%Y-%m-%d %H:%M:%S"))


def Api_ReAddr(str_addr, zipcode, url_api):
    headers = {'Content-Type':'application/json'}
    data =  {
             "MWHEADER": {
                     "MSGID": "ZZ{0}".format(random.randint(0, 9999)) ,
                     "SOURCECHANNEL": "CATHAYINS",
                     "TXNSEQ": get_timestamp('TXNSEQ')
                     },
             "TRANRQ": {
                     "MethodName": "addressNormalize",
                     "ZsParameter": {
                             "Address":str_addr,
                             "ZipCode": zipcode
                             }
                     }
             }
    try:
        res = requests.post(url_api, headers = headers, json = data)
        res = res.json()
        return res
    except Exception as e:
        logging.info(f'[ERROR] {e}')

    

def Api_Latlng(str_addr):
    url= os.environ['apigateway'] #'http://sbz-rs-gateway-smartbiz.tokd.cathay-ins.com.tw/tool/gateway'
    headers = {'Content-Type':'application/json'}
    data=  {
          "MWHEADER": {
            "MSGID": "SBZ-C-ADRSUTILO001",
            "SOURCECHANNEL": "MID-JV-CMN-CM",
            "TXNSEQ": get_timestamp('TXNSEQ')
          },
          "TRANRQ": {
             "ADDRESS": str_addr
          }
        }
    res = requests.post(url, headers = headers, json = data)
    res = res.json()
    return res

#{ "do":"ReAddr" ,"tbname":"address_table","colname":"ori_address","conditions": {"ori_address":"桃園市三民里園一路171號1樓"}
def Posg_Conn(tbname, colname, condition):
    start = time.time()
    keyColMapping = {'City':'city','Area':'county','Village':'village','Neighborhood':'neighbor','Road':'road_street','Lane':'lane','Alley':'alley','No':'house_no','NoBreach':'house_no1','Floor':'floor','FloorBreach':'floor_extn','Room':'room','RoomBreach':'room1'}

    # @ = '
    sql = 'SELECT * FROM {tbname} WHERE {condition}'.format(tbname = tbname, condition = condition) 
    logging.debug('[Debug] '+str(sql))
    sql = sql.replace("393431", "'")
    logging.debug('[Debug] '+str(sql))
#    for k,v in condition.items():
#        sql=sql+f"{k} <> '{v}' AND"
    df = pd.read_sql(sql, engine)    
    addr_list = df[colname].values
    logging.info('[INFO] Api_ReAddr start...')
    ReAddr_start = time.time()
    for addr in addr_list:
        reAddr = Api_ReAddr(addr, '', os.environ['apiaddr'])
        if reAddr['MWHEADER']['RETURNCODE'] == '0000':
            reAddr = reAddr['TRANRS']
            for key, value in reAddr.items():
                try:
                    df.loc[df[colname] == addr, keyColMapping[key]] = value
                    df.loc[df[colname] == addr, 'normal_yn'] = 'Y'
                    df.loc[df[colname] == addr, 'process_time'] = get_timestamp('process_time')
                except:
                    pass
        else:
            df.loc[df[colname] == addr, 'normal_yn'] = 'N'
            df.loc[df[colname] == addr, 'process_time'] = get_timestamp('process_time') 
    logging.info('[INFO] Api_ReAddr End')
    logging.info('[INFO] update Start')
    ReAddr_end=time.time()
    ReAddr_time=ReAddr_end-ReAddr_start
    try:
        #df.to_sql(tbname, con = conn, if_exists = 'replace', index = False)
        logging.debug('[Debug] connectDB ...')
        conn = connectDB()
        cur = conn.cursor()
        logging.debug('[Debug] connectDB success')
        upcol = ['city', 'county', 'village',
           'neighbor', 'road_street', 'lane', 'alley', 'house_no', 'house_no1',
           'floor', 'floor_extn', 'room', 'room1', 'normal_yn', 'longitud',
           'latitude', 'lnglat_yn', 'process_time','ori_address','yyyymmdd']
        sql = f"UPDATE {tbname} SET"
        for col in upcol[:-2]:
            sql += f' {col} = %s ,'
        sql=sql[:-1]+f' WHERE {colname} = %s AND yyyymmdd = %s'
        logging.debug('[Debug] '+str(sql))
        val=list()
        for x in df[upcol].values:
            x[-1]=x[-1].strftime("%Y-%m-%d")
            val.append(tuple(x))
        logging.debug('[Debug] '+str(val[:10]))
        logging.debug('[Debug] execute ...')
        cur.executemany(sql, val)
        logging.debug('[Debug] execute success')
        conn.commit()
        logging.debug('[Debug] commit success')
        conn.close()
        logging.debug('[Debug] connectDB close')
        end=time.time()
        # df[upcol].to_csv(f'/ftpdata/ftphome/sbz/{tbname}.csv',index=False,encodinf='utf-8')
        logging.info('[INFO] update End')
        return {'status':200,'ReAddr_time':ReAddr_time,'update_time':end-ReAddr_end ,'total_time':end-start}
    except Exception as e:
        logging.info(f'[ERROR] {e}')
        return 'Conn_error', 500

def getData(data):
    logging.info('[INPUT] '+str(data))
    tbname, colnames, condition=data['tbname'], data['colname'], data['condition']
    sql = f'SELECT {colnames} FROM {tbname} WHERE {condition}'
    logging.debug('[Debug] '+str(sql))
    sql = sql.replace("393431", "'")
    logging.debug('[Debug] '+str(sql))
#    for k,v in condition.items():
#        sql=sql+f"{k} <> '{v}' AND"
    df = pd.read_sql(sql, engine)
    df.to_csv(f'/DS_ftp/sbz/{tbname}.csv',index=False,header=None,sep='\u0001')
    return {'status':'ok','return_code':200}

def Posg_latlng(tbname, colname, condition):
    start = time.time()
    
    sql = 'SELECT * FROM {tbname} WHERE {condition}'.format(tbname = tbname, condition = condition) 
    logging.debug('[Debug] '+str(sql))
    sql = sql.replace("393431", "'")
    logging.debug('[Debug] '+str(sql))
#    for k,v in condition.items():
#        sql=sql+f"{k} <> '{v}' AND"
    df = pd.read_sql(sql, engine)  
    colname="concat_address"
    addr_list = df[colname].values

    logging.info('[INFO] Api_latlng start...')
    latlng_start = time.time()
    for addr in addr_list:
        reAddr = Api_Latlng(addr)
        if reAddr['MWHEADER']['RETURNCODE']=='0000':
            reAddr = reAddr['TRANRS']
            df.loc[df[colname] == addr, 'longitud'] = reAddr['LONGITUDE']
            df.loc[df[colname] == addr, 'latitude'] = reAddr['LATITUDE']
            df.loc[df[colname] == addr, 'lnglat_yn'] = 'Y'
            df.loc[df[colname] == addr, 'process_time'] = get_timestamp('process_time')
        else:
            df.loc[df[colname] == addr, 'lnglat_yn'] = 'N'
            df.loc[df[colname] == addr, 'process_time'] = get_timestamp('process_time') 
    
    logging.info('[INFO] Api_Latlng End')
    logging.info('[INFO] update Start')
    latlng_end=time.time()
    latlng_time=latlng_end-latlng_start

    try:
        #df.to_sql(tbname, con = conn, if_exists = 'replace', index = False)
        logging.debug('[Debug] connectDB ...')
        conn = connectDB()
        cur = conn.cursor()
        logging.debug('[Debug] connectDB success')
        upcol = ['longitud', 'latitude', 'lnglat_yn', 'process_time','ori_address','yyyymmdd']
        
        sql = f"UPDATE {tbname} SET"
        for col in upcol[:-2]:
            sql += f' {col} = %s ,'
        sql=sql[:-1]+f' WHERE {colname} = %s AND yyyymmdd = %s'
        logging.debug('[Debug] '+str(sql))
        val=list()

        for x in df[upcol].values:
            x[-1]=x[-1].strftime("%Y-%m-%d")
            val.append(tuple(x))
        logging.debug('[Debug] '+str(val[:10]))
        logging.debug('[Debug] execute ...')
        cur.executemany(sql, val)
        logging.debug('[Debug] execute success')
        conn.commit()
        logging.debug('[Debug] commit success')
        conn.close()
        logging.debug('[Debug] connectDB close')
        end=time.time()
        # df[upcol].to_csv(f'/ftpdata/ftphome/sbz/{tbname}.csv',index=False,encodinf='utf-8')
        logging.info('[INFO] update End')

        return {'status':200,'Latlng_time':latlng_time,'update_time':end-latlng_end ,'total_time':end-start}

    except:
        return 'Conn_error', 500

def mainFunc(data):
    logging.info('[INPUT] '+str(data))
    if data['do'] == "ReAddr":
        return Posg_Conn(data['tbname'], data['colname'], data['condition'])
    elif data['do'] == "latlng":
        return Posg_latlng(data['tbname'], data['colname'], data['condition'])
    else:
        return 'api not found', 500
    

   




    
    
    
    
    
    
    
    
    
    
    
    
    

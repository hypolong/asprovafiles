import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from datetime import datetime, timezone
import shutil
from zoneinfo import ZoneInfo
import time

#function for getting plex info and update asprova***************************
def fetch_plex_production_data(jobNum:str,copyfilename:str):

    #get the " 実績開始日時	実績終了日時	実績数量 " 
    #set the " 実績開始日時	実績終了日時	実績数量  更新日時 "   
    # 1.get the job key
    PLEX_API="https://nswmes.on.plex.com/api/datasources/5197/execute"
    headers = {
            "Content-Type": "application/json"
    }

    body={
        "inputs": {
            "Job_No": jobNum
        }
    }
    
    jobkey=0
    try:
        response = requests.post(PLEX_API, auth = HTTPBasicAuth("NSWTrainingPCN3PWs@plex.com", "4b3e197-1b48-4"), headers=headers,json=body)
        jobkey = int(response.json()["tables"][0]["rows"][0][0])
    except Exception as e:
        print("get job key failed:", e)
        return False

    # 2.get the job deteils seting
    jobInfoSet=[]

    PLEX_API="https://nswmes.on.plex.com/api/datasources/4422/execute"
    body={
        "inputs": {
            "Job_Key": jobkey
        }
    }

    try:
        response = requests.post(PLEX_API, auth = HTTPBasicAuth("NSWTrainingPCN3PWs@plex.com", "4b3e197-1b48-4"), headers=headers,json=body)
        if str(response.status_code)=="200" or str(response.status_code)=="201":
            table = response.json()["tables"][0]
            columns = table["columns"]
            rows = table["rows"]

            # serach the index
            col_Job_No = columns.index("Job_No")
            col_Op_No = columns.index("Op_No")
            col_index_completed_quantity = columns.index("Inventory")
            col_index_Start_Date = columns.index("Start_Date")
            col_index_Complete_Date = columns.index("Complete_Date")

            for items in rows:
                # 1.tran the utc time for start time
                start_Date=items[col_index_Start_Date]
                if  not start_Date is None:
                    start_Date = datetime.strptime(start_Date, "%Y-%m-%dT%H:%M:%SZ")
                    start_Date = start_Date.replace(tzinfo=timezone.utc)

                    # tran to jp time
                    start_Date = start_Date.astimezone(ZoneInfo("Asia/Tokyo"))

                    # format the time 
                    start_Date = f"{start_Date.year}/{start_Date.month}/{start_Date.day} {start_Date:%H:%M}"

                # 2.tran the utc time for end time
                end_Date=items[col_index_Complete_Date]
                if not end_Date is None:
                    end_Date = datetime.strptime(end_Date, "%Y-%m-%dT%H:%M:%SZ")
                    end_Date = end_Date.replace(tzinfo=timezone.utc)

                    # tran to jp time
                    end_Date = end_Date.astimezone(ZoneInfo("Asia/Tokyo"))

                    # format the time 
                    end_Date = f"{end_Date.year}/{end_Date.month}/{end_Date.day} {end_Date:%H:%M}"

                jobInfoSet.append([items[col_Job_No], str(items[col_Job_No]) + ":" + str(items[col_Op_No]),
                    items[col_index_completed_quantity],start_Date,end_Date
                ])
        else:
            return False
    except Exception as e:
        print("get job detail info failed:", e)
        return False
    
    
    jobInfoSet_df = pd.DataFrame(jobInfoSet, columns=[
        "オーダコード", "コード", "実績数量", "実績開始日時", "実績終了日時"
    ])

    # # 3. update asprova, ignore the time but just the completed quantity
    # #write into csv file for asprova ===============
    df = pd.read_csv(copyfilename,encoding="cp932")

    # set to the same type for mapping
    df["オーダコード"] = df["オーダコード"].astype(str)
    df["コード"] = df["コード"].astype(str)
    jobInfoSet_df["オーダコード"] = jobInfoSet_df["オーダコード"].astype(str)
    jobInfoSet_df["コード"] = jobInfoSet_df["コード"].astype(str)

    df = df.merge(
        jobInfoSet_df,
        on=["オーダコード", "コード"],
        how="left",
        suffixes=("", "_mes")
    )

    update_cols = ["実績数量", "実績開始日時", "実績終了日時"]
    for col in update_cols:
        df[col] = df[f"{col}_mes"].combine_first(df[col])


    df.drop(columns=[col for col in df.columns if col.endswith("_mes")], inplace=True)
    df.to_csv(copyfilename, index=False, encoding="cp932")


if __name__ == "__main__":
    # main function**********

    # synchro the data by 10 minutes
    while True: 
        # copy the origin csv file
        orignfilename='C://Program Files//Asprova Corporation//Asprova//Samples//plexpj//output//jobs.csv'
        copyfilename='C://Program Files//Asprova Corporation//Asprova//Samples//plexpj//output//jobs-modifiedBy'+ datetime.now().strftime("%Y%m%d%H%M%S") +'.csv'
        shutil.copyfile(orignfilename, copyfilename)

        #read the csv or DB
        df = pd.read_csv(copyfilename,encoding="cp932")
        grouped = df.groupby("オーダコード")

        # deal by order unit
        for name, group in grouped:
            for row in group.itertuples(index=False):
                fetch_plex_production_data(row.オーダコード,orignfilename)
                break
        print("backup the lastest jobs.csv to " + copyfilename + " and write to jobs.csv completed")
        time.sleep(600)

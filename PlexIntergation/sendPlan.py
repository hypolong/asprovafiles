import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from datetime import datetime
import time

#function for modify plex jobs  ***************************
def modify_plex_source_data(jobNum:str,quantity:int,detailInfo:list,jobEarliestStartDateTime:str,dueDate:str,partId:str,jobAddorNot:bool):
    jobType="Stock"
    jobPriority="Medium"

    if jobAddorNot:
        # 1. create the job firstly
        PLEX_API= "https://connect.plex.com/scheduling/v1/jobs"

        headers = {
            "Content-Type": "application/json",
            "X-Plex-Connect-Api-Key":"wj1pzuvqwQuICDmQLaeYtD3q0W479vMr",
            "X-Plex-Connect-Tenant-Id":"6c7168ec-c430-494d-8fcc-4d789b447964"
        }

        try:
            body={
                "partId": partId,
                "dueDate": dueDate,
                "quantity": quantity,
                "jobType": jobType,
                "jobNumber": jobNum,
                "priority": jobPriority,
                "earliestStartDateTime": jobEarliestStartDateTime
            }

            # justify firstly if the source is enough
            response = requests.post(PLEX_API,headers=headers,json=body)
            
            if not str(response.status_code)=="200" and not str(response.status_code)=="201":
                print("add job failed for some reason:",response.json()["errors"][0]["message"])
                return False
            
        except Exception as e:
            print("add job failed,job exists or can not add by some reason", e)
            return False
    
    # 2.get the job id
    PLEX_API="https://connect.plex.com/scheduling/v1/jobs"
    jobid=""
    try:
        params = {'jobNumber': jobNum}
        response = requests.get(PLEX_API,headers=headers,params=params)
        jobid = str(response.json()[0]["id"])
    except Exception as e:
        print("get job id failed:", e)
        return False

    # 3. dispath the job to workcenter
    # firstly, to get the operation seting for now
    PLEX_API="https://connect.plex.com/scheduling/v1/jobs/"+ jobid+"/operations"
    jobOpsInfo=""
    try:
        response = requests.get(PLEX_API,headers=headers)
        if str(response.status_code)=="200" or str(response.status_code)=="201":
            jobOpsInfo = response.json()
        else:
            return False
    except Exception as e:
        print("get job operation info failed:", e)
        return False


    # modify the job operations for startDateTime
    PLEX_API="https://connect.plex.com/scheduling/v1/jobs/"+ jobid+"/operations-schedule"
    try:
        body=[]
        for items in jobOpsInfo:
            updateTemplate={
                "jobOperationId": "a8407d96-6609-43bc-b606-a09f1dd17b5d",
                "jobOperationStatus": "New",
                "scheduleDetails": [
                {
                    "workcenterId": "224772fc-15ba-4674-92a4-6689211e00ba",
                    "startDateTime": "2026-04-27T14:25:00Z",
                    "runLength": 30
                }
                ]
            }
            updateTemplate["jobOperationId"]=items["jobOperationId"]
            updateTemplate["jobOperationStatus"]=items["jobOperationStatus"]
            findWorkcenter=0

            # find the process info by detailInfo
            for rows in detailInfo:
                if rows[0]==str(items["jobOperationNumber"]):
                    updateTemplate["scheduleDetails"][0]["startDateTime"]=rows[2]
                    updateTemplate["scheduleDetails"][0]["runLength"]=int(rows[3])

            # this can use API to get the workcentid and mapping between asprova and plex in the future
            if str(items["operationCode"]).find("press")>=0:
                updateTemplate["scheduleDetails"][0]["workcenterId"]="2d26cb8f-2bc3-4f5c-ad6a-e84a7d414cde"
                findWorkcenter=1
            elif str(items["operationCode"]).find("welding")>=0:
                updateTemplate["scheduleDetails"][0]["workcenterId"]="c05ae26a-025d-4b35-b013-a6d1ab94908c"
                findWorkcenter=1
            elif str(items["operationCode"]).find("painting")>=0:
                updateTemplate["scheduleDetails"][0]["workcenterId"]="224772fc-15ba-4674-92a4-6689211e00ba"
                findWorkcenter=1
            elif str(items["operationCode"]).find("assembly")>=0:
                updateTemplate["scheduleDetails"][0]["workcenterId"]="0bc6e9fb-c43d-421d-a1ca-f0a52d838e8f"
                findWorkcenter=1
            else:
                updateTemplate["scheduleDetails"][0]["workcenterId"]=""
                findWorkcenter=0

            if findWorkcenter==1:
                body.append(updateTemplate)

        response = requests.post(PLEX_API,headers=headers,json=body)
        if not str(response.status_code)=="200" and not str(response.status_code)=="201":
            # write json to text for verify
            with open("result.json", 'w') as file:
                file.write(str(body).replace("'","\"") + "\n")
                file.write(str(response.json()))
            return False
        else:
            print("*************update completed!")
            return True
    except Exception as e:
        print("update job operations failed:", e)
        return False

if __name__ == "__main__":

    while True:
        #read the csv or DB
        orignfilename='C://Program Files//Asprova Corporation//Asprova//Samples//plexpj//output//jobs.csv'
        df = pd.read_csv(orignfilename,encoding="cp932")
        grouped = df.groupby("オーダコード")

        for name, group in grouped:
            processInfo=[]
            lastrowIndex=0
            for row in group.itertuples(index=False):
                processID=str(row.コード)
                processID=processID[processID.find(":")+1:]
                processInfo.append([processID,float(row.製造数量),datetime.strptime(str(row.製造開始日時), "%Y/%m/%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%SZ"),int(row.製造時間)/60])

                lastrowIndex += 1
                # the last row is the last process
                if lastrowIndex==len(group):
                    #find the parts id firstly
                    PLEX_API= "https://connect.plex.com/inventory/v1/inventory-definitions/parts"
                    headers = {
                        "Content-Type": "application/json",
                        "X-Plex-Connect-Api-Key":"wj1pzuvqwQuICDmQLaeYtD3q0W479vMr",
                        "X-Plex-Connect-Tenant-Id":"6c7168ec-c430-494d-8fcc-4d789b447964"
                    }

                    partID=""
                    try:
                        params = {'partNumber': str(row.主産物品目コード)}
                        
                        # get the part id
                        response = requests.get(PLEX_API,headers=headers,params=params)

                        if str(response.status_code)=="200" or str(response.status_code)=="201":
                            partID=str(response.json()[0]["partId"])
                        else:
                            print(response.json())
                            break
                    except Exception as e:
                        print("add job and set process failed,job exists or can not add by some reason", e)
                        break
                    
                    # call the modify function
                    modify_plex_source_data(row.オーダコード,int(row.製造数量),processInfo,datetime.strptime(str(row.製造開始日時), "%Y/%m/%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%SZ"),datetime.strptime(str(row.製造終了日時), "%Y/%m/%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%SZ"),partID,True)

        time.sleep(60)

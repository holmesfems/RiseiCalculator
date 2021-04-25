import numpy as np
import numpy.linalg as LA
import urllib.request, json, time, os, copy, sys
from scipy.optimize import linprog
from collections import defaultdict as ddict
import random
import pandas as pd

global penguin_url, headers, LanguageMap
penguin_url = 'https://penguin-stats.io/PenguinStats/api/v2/'
headers = {'User-Agent':'ArkPlanner'}
LanguageMap = {'CN': 'zh', 'US': 'en', 'JP': 'ja', 'KR': 'ko'}

Price = dict()
with open('price.txt', 'r', encoding='utf8') as f:
    for line in f.readlines():
        name, value = line.split()
        Price[name] = int(value)
        
def get_json(s,AdditionalReq=None):
    if not AdditionalReq == None:
        s += "?" + "&".join(['%s=%s'%(x,AdditionalReq[x]) for x in AdditionalReq])
    req = urllib.request.Request(penguin_url + s, None, headers)
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode())

class RiseiCalculator(object):
    def __init__(self,
                 filter_freq=200,
                 filter_stages=[],
                 url_stats='result/matrix?show_closed_zone=true',
                 url_rules='formula',
                 path_stats='data/matrix.json',
                 path_rules='data/formula.json',
                 TargetServer = 'CN',
                 update=False,
                 banned_stages={},
#                 expValue=30,
                 ConvertionDR=0.18,
                 minTimes = 1000,
                 display_main_only=True):
        """
        Object initialization.
        Args:
            filter_freq: int or None. The lowest frequence that we consider.
                No filter will be applied if None.
            url_stats: string. url to the dropping rate stats data.
            url_rules: string. url to the composing rules data.
            path_stats: string. local path to the dropping rate stats data.
            path_rules: string. local path to the composing rules data.
        """
        self.get_item_id()
        self.banned_stages = banned_stages # for debugging
        self.display_main_only = display_main_only
        self.ConvertionDR = ConvertionDR
        self.minTimes = minTimes
        self.TargetServer = TargetServer
        self.ValueTarget = ['基础作战记录', '初级作战记录', '中级作战记录', '高级作战记录', 
            '赤金','龙门币1000',
            '源岩', '固源岩', '固源岩组', '提纯源岩', 
            '破损装置', '装置', '全新装置', '改量装置', 
            '酯原料', '聚酸酯', '聚酸酯组', '聚酸酯块', 
            '代糖', '糖', '糖组', '糖聚块', 
            '异铁碎片', '异铁', '异铁组', '异铁块', 
            '双酮', '酮凝集', '酮凝集组', '酮阵列', 
            '扭转醇', '白马醇',
            '轻锰矿', '三水锰矿',
            '研磨石', '五水研磨石',
            'RMA70-12', 'RMA70-24',
            '凝胶', '聚合凝胶',
            '炽合金', '炽合金块',
            '晶体元件', '晶体电路',
            '聚合剂', '双极纳米片', 'D32钢','晶体电子单元',
            '技巧概要·卷1', '技巧概要·卷2', '技巧概要·卷3']
        self.name_to_index = {x:self.ValueTarget.index(x) for x in self.ValueTarget}
        self.id_to_index = {x:self.name_to_index[self.item_id_to_name[x]["zh"]] for x in [self.item_name_to_id["zh"][y] for y in self.ValueTarget]}
        self.TotalCount = len(self.ValueTarget)
        #self.update(force=update)

    def get_item_id(self):
        items = get_json('items')
        item_array, item_id_to_name = [], {}
        item_name_to_id = {'id': {},
                           'zh': {},
                           'en': {},
                           'ja': {},
                           'ko': {}}

        additional_items = [
                            {'itemId': '4001', 'name_i18n': {'ko': '용문폐', 'ja': '龍門幣', 'en': 'LMD', 'zh': '龙门币'}},
                            {'itemId': '0010', 'name_i18n': {'ko': '작전기록', 'ja': '作戦記録', 'en': 'Battle Record', 'zh': '作战记录'}}
                           ]
        for x in items + additional_items:
            item_array.append(x['itemId'])
            item_id_to_name.update({x['itemId']: {'id': x['itemId'],
                                                  'zh': x['name_i18n']['zh'],
                                                  'en': x['name_i18n']['en'],
                                                  'ja': x['name_i18n']['ja'],
                                                  'ko': x['name_i18n']['ko']}})
            item_name_to_id['id'].update({x['itemId']:          x['itemId']})
            item_name_to_id['zh'].update({x['name_i18n']['zh']: x['itemId']})
            item_name_to_id['en'].update({x['name_i18n']['en']: x['itemId']})
            item_name_to_id['ja'].update({x['name_i18n']['ja']: x['itemId']})
            item_name_to_id['ko'].update({x['name_i18n']['ko']: x['itemId']})

        self.item_array = item_array
        self.item_id_to_name = item_id_to_name
        self.item_name_to_id = item_name_to_id
        self.item_dct_rv = {v: k for k, v in enumerate(item_array)} # from id to idx
        self.item_name_rv = {item_id_to_name[v]['zh']: k for k, v in enumerate(item_array)} # from (zh) name to id

    def _GetMatrixNFormula(self):
        """
        import formula data and matrix data
        """
        AllstageList = get_json("stages")
        #イベントステージを除外
        MainStageList = [x for x in AllstageList if x["stageType"] in ["MAIN","SUB"]]
        #print(MainStageList)
        stageFilter = ",".join([x["stageId"] for x in MainStageList])
        itemFilter = ",".join([self.item_name_to_id["zh"][x] for x in self.ValueTarget])

        additionalHeader = {"stageFilter":stageFilter,"itemFilter":itemFilter,"server":self.TargetServer}
        #ドロップデータ取得
        matrix = get_json('result/matrix',additionalHeader)
        #合成レシピ 副産物確率取得
        formula = get_json('formula')

        self.matrix = matrix
        self.formula = formula
        self.stages = MainStageList
        self.stageId_to_name = {x["stageId"]:x["code_i18n"]["zh"] for x in self.stages}
        self.stageName_to_Id = {x["code_i18n"]["zh"]:x["stageId"] for x in self.stages}
        #print(self.item_id_to_name[matrix["matrix"][0]["itemId"]])
        #print(self.item_name_to_id["zh"].keys())
        #print(self.name_to_index)
        #print(self.id_to_index)

    def _GetConvertionMatrix(self):
        """
        Get convertion part of value_matrix
        """
        arraylist = []
        # 経験値換算
        # 基础作战记录*2=初级作战记录
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["基础作战记录"]] = -2
        arr[self.name_to_index["初级作战记录"]] = 1
        arraylist.append(arr)

        # 初级作战记录*2.5=中级作战记录
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["初级作战记录"]] = -2.5
        arr[self.name_to_index["中级作战记录"]] = 1
        arraylist.append(arr)

        # 中级作战记录*2=高级作战记录
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["中级作战记录"]] = -2
        arr[self.name_to_index["高级作战记录"]] = 1
        arraylist.append(arr)

        # 赤金*2 = 龙门币1000
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["赤金"]] = -2
        arr[self.name_to_index["龙门币1000"]] = 1
        arraylist.append(arr)
    
        # 素材合成換算
        for item in self.formula:
            arr = np.zeros(self.TotalCount)
            arr[self.name_to_index[item["name"]]] = -1
            arr[self.name_to_index["龙门币1000"]] = item["goldCost"]/1000
            for costItem in item["costs"]:
                arr[self.name_to_index[costItem["name"]]] = costItem["count"]

            #副産物を考慮
            exarr = np.zeros(self.TotalCount)
            for exItem in item["extraOutcome"]:
                exarr[self.name_to_index[exItem["name"]]] = exItem["weight"]/item["totalWeight"]
            
            arraylist.append(arr-exarr*self.ConvertionDR)
        
        # 本の合成
        # 技1*3=技2
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["技巧概要·卷1"]] = 3
        arr[self.name_to_index["技巧概要·卷2"]] = -1-self.ConvertionDR
        arraylist.append(arr)

        # 技2*3=技3
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["技巧概要·卷2"]] = 3
        arr[self.name_to_index["技巧概要·卷3"]] = -1-self.ConvertionDR
        arraylist.append(arr)

        return (np.array(arraylist),np.zeros(len(arraylist)))
    
    def _GetConstStageMatrix(self):
        arraylist = []
        riseilist = []
        #LS-5
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["初级作战记录"]] = 1
        arr[self.name_to_index["中级作战记录"]] = 1
        arr[self.name_to_index["高级作战记录"]] = 3
        arr[self.name_to_index["龙门币1000"]] = 0.36
        arraylist.append(arr)
        riseilist.append(30)

        #CE-5
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["龙门币1000"]] = 7.5
        arraylist.append(arr)
        riseilist.append(30)

        #CA-5
        arr = np.zeros(self.TotalCount)
        arr[self.name_to_index["技巧概要·卷1"]] = 1.5
        arr[self.name_to_index["技巧概要·卷2"]] = 1.5
        arr[self.name_to_index["技巧概要·卷3"]] = 2
        arr[self.name_to_index["龙门币1000"]] = 0.36
        arraylist.append(arr)
        riseilist.append(30)
        
        return (np.array(arraylist),np.array(riseilist))

    def _getValidStageList(self):
        #ステージのカテゴリ化
        #スマートなやり方が分からなかったので手打ちで
        #'Stages' 'Items'の他に、試行回数条件を満たしたステージIdのみを入れる'ValidIds'も追加される
        self.stage_Category_dict = {
            '源岩':{
                'Stages':['R8-3','4-6','7-2','6-5','5-1','2-4','S2-12','S3-7','5-10','S5-1','S6-2','1-7','7-16'], \
                'Items':['源岩', '固源岩', '固源岩组', '提纯源岩'] 
            },
            '装置':{
                'Stages':['4-10','7-9','7-15','5-10','6-16','4-10','M8-8','7-9','3-4','S3-4','6-11'],
                'Items':['破损装置', '装置', '全新装置', '改量装置'] 
            },
            '酯':{
                'Stages':['6-4','3-8','7-4','5-3','2-6','S3-2','6-5','1-8'],
                'Items':['酯原料', '聚酸酯', '聚酸酯组', '聚酸酯块']
            },
            '糖':{
                'Stages':['5-2','4-2','M8-7','7-12','6-3','2-5'],
                'Items':['代糖', '糖', '糖组', '糖聚块']
            },
            '异铁':{
                'Stages':['5-5','S4-1','7-18','6-10','2-8','S3-3','M8-1','5-7'],
                'Items':['异铁碎片', '异铁', '异铁组', '异铁块']
            },
            '酮':{
                'Stages':['4-5','5-8','JT8-3','3-1','7-14','6-8','3-7','7-18','6-16','7-12'],
                'Items':['双酮', '酮凝集', '酮凝集组', '酮阵列']
            },
            '醇':{
                'Stages':['4-4','R8-2','7-5','6-11','5-4','2-9'],
                'Items':['扭转醇', '白马醇']
            },
            '锰':{
                'Stages':['4-7','6-2','R8-10','7-16','3-2','5-6'],
                'Items':['轻锰矿', '三水锰矿']
            },
            '研磨石':{
                'Stages':['7-17','4-8','5-7','3-3','6-14'],
                'Items':['研磨石', '五水研磨石']
            },
            'RMA':{
                'Stages':['4-9','6-15','R8-9','7-10','2-10'],
                'Items':['RMA70-12', 'RMA70-24']
            },
            '凝胶':{
                'Stages':['JT8-2','7-8','S5-7','S4-10','R8-8'],
                'Items':['凝胶', '聚合凝胶']
            },
            '炽合金':{
                'Stages':['R8-7','S5-8','6-12','S3-6'],
                'Items':['炽合金', '炽合金块']
            },
            '晶体':{
                'Stages':['R8-11','S5-9','S3-7'],
                'Items':['晶体元件', '晶体电路']
            }
        }
        #カテゴリキー 基準選びはカテゴリ毎に一つだけ抽選される
        self.stage_Category_keys = list(self.stage_Category_dict.keys())

        """
        stage dict:ステージごとの情報を取得する
        Key:stageId
        Value:{
            array: ndarray,各素材のドロップ率をValueTarget順に記載
            apCost: int, 理性消費
            name: str,ステージ名
            minTimes: int, 各素材の内、報告の最小試行回数
        }
        """
        stage_dict = {}
        for item in self.matrix["matrix"]:
            if not item["stageId"] in stage_dict.keys():
                #initialize
                stage_info = {}
                stage_info["array"] = np.zeros(self.TotalCount)
                #print(item["stageId"])
                stage_info["apCost"] = [x["apCost"] for x in self.stages if x["stageId"] == item["stageId"]][0]
                stage_info["name"] = self.stageId_to_name[item["stageId"]]
                stage_info["array"][self.name_to_index["龙门币1000"]] = stage_info["apCost"] *0.012
                stage_info["minTimes"] = 0
                stage_dict[item["stageId"]] = stage_info
            stage_dict[item["stageId"]]["array"][self.id_to_index[item["itemId"]]] += item["quantity"]/item["times"]
            if stage_dict[item["stageId"]]["minTimes"] == 0 or item["times"] < stage_dict[item["stageId"]]["minTimes"]:
                stage_dict[item["stageId"]]["minTimes"] = item["times"]
        #print(stage_dict)
        #試行回数条件を満たしているステージのみ出力&Id順にソートしておく
        self.stage_dict = {key:value for key,value in sorted(stage_dict.items(),key=lambda x:x[0]) if value["minTimes"] >= self.minTimes}
        self.valid_stages = list(self.stage_dict.keys())
        self.valid_stages_getindex = {x:self.valid_stages.index(x) for x in self.valid_stages}
        #add 'ValidIds' for StageCategory
        for item in self.stage_Category_keys:
            self.stage_Category_dict[item]['ValidIds'] = [x for x in self.valid_stages if self.stage_dict[x]["name"] in self.stage_Category_dict[item]['Stages']]

    #seedsからステージのドロ率行列を取得
    #seedsは選ぶ基準ステージのvalid_stages内のindexを意味している
    def _getStageMatrix(self,seeds):
        arraylist = []
        riseilist = []
        for index in seeds:
            arraylist.append(self.stage_dict[self.valid_stages[index]]["array"])
            riseilist.append(self.stage_dict[self.valid_stages[index]]["apCost"])
        return (np.array(arraylist),np.array(riseilist))
    
    def _detMatrix(self,vstackTuple):
        return LA.det(np.vstack(vstackTuple))
    
    def _seed2StageName(self,seeds):
        return [self.stageId_to_name[self.valid_stages[x]] for x in seeds]

    def _getValues(self,vstackTuple,riseiArrayList):
        #線型方程式で理性価値を解く
        return LA.solve(np.vstack(vstackTuple),np.concatenate(riseiArrayList))

    def _getStageValues(self,valueArray):
        #解いた理性価値を使い、ステージごとの理性効率を求める
        #理性効率=Sum(理性価値×ドロ率)/理性消費
        #効率が1より上回るステージがあれば、まだ最適ではないと言える
        return {x:np.dot(valueArray,self.stage_dict[x]["array"].T)/self.stage_dict[x]["apCost"] for x in self.valid_stages}
    
    def _getCategoryFromStageId(self,stageId):
        return [x for x in self.stage_Category_keys if stageId in self.stage_Category_dict[x]['ValidIds']]

    def Calc(self):
        self._GetMatrixNFormula()
        ConvertionMatrix,ConvertionRisei = self._GetConvertionMatrix()
        ConstStageMatrix,ConstStageRisei = self._GetConstStageMatrix()
        #print(self.matrix)
        self._getValidStageList()
        #print(self.stage_dict)

        #理性計算に必要なステージ数
        stages_need = self.TotalCount - len(ConvertionMatrix) - len(ConstStageMatrix)
        print("必要ステージ数:",stages_need)
        det = 0
        #stageMatrix = []
        #stageRisei = []
        while(abs(det) < 50):
            seeds = [-1]*stages_need
            for i in range(stages_need):
                randomStageId = random.choice(self.stage_Category_dict[self.stage_Category_keys[i]]["ValidIds"])
                seeds[i] = self.valid_stages_getindex[randomStageId]
            stageMatrix, stageRisei = self._getStageMatrix(seeds)
            det = self._detMatrix((ConvertionMatrix,ConstStageMatrix,stageMatrix))
        
        print("Seed Stages:",self._seed2StageName(seeds),"det=",det)
        seedValues = self._getValues((ConvertionMatrix,ConstStageMatrix,stageMatrix),[ConvertionRisei,ConstStageRisei,stageRisei])
        print("Seed Values:",seedValues)
        #print(self._getStageValues(seedValues))
        stageValues = self._getStageValues(seedValues)
        #理性効率の最大を求める これを1にするように後で調整
        maxValue = max(stageValues.items(),key=lambda x: x[1])
        if maxValue[1] > 1+1e-5:
            print(maxValue,'基準より高い効率を検出:',self.stageId_to_name[maxValue[0]])

        while(maxValue[1] > 1+1e-5):
            #理性効率が最大になるステージを、同カテゴリのステージと差し替える
            #カテゴリが複数該当する場合、全て試してみたのち理性効率が小さい方を選ぶ
            #最大理性効率が1でなければ、これを繰り返す
            targetCategories = self._getCategoryFromStageId(maxValue[0])
            print('基準マップ差し替え：ターゲットカテゴリ',targetCategories)
            if len(targetCategories) == 0:
                print('カテゴリから外れたマップを検出、計算を中断します')
                print('マップ'+self.stageId_to_name[maxValue[0]]+'は、何を稼ぐステージですか？')
                print('RiseiCalculator.pyで、228行あたりを編集し、情報を追加してください')
                return
            maxValuesDict = {}
            for item in targetCategories:
                newSeeds = np.copy(seeds)
                targetIndex = self.stage_Category_keys.index(item)
                newSeeds[targetIndex] = self.valid_stages_getindex[maxValue[0]]
                #print(newSeeds)
                newMatrix,newRisei = self._getStageMatrix(newSeeds)
                det = self._detMatrix((ConvertionMatrix,ConstStageMatrix,newMatrix))
                #print(det)
                if(abs(det) < 1):
                    continue
                newSeedValues = self._getValues((ConvertionMatrix,ConstStageMatrix,newMatrix),[ConvertionRisei,ConstStageRisei,newRisei])
                newStageValues = self._getStageValues(newSeedValues)
                newMaxValue = max(newStageValues.items(),key=lambda x:x[1])
                maxValuesDict[item]=newMaxValue
            #最大理性効率が最も小さいものが、一番良い差し替え
            print('差し替え後、最大効率一覧:',maxValuesDict)
            best_maxValue = min(maxValuesDict.items(),key = lambda x:x[1][1])
            targetIndex = self.stage_Category_keys.index(best_maxValue[0])
            seeds[targetIndex] = self.valid_stages_getindex[maxValue[0]]
            print('差し替え完了、現在の最大効率マップ:',best_maxValue)
            maxValue = best_maxValue[1]
        #最適なseedを使い再度効率計算
        #場合によっては無駄になるけど考えるのがめんどくさくなったから計算の暴力で
        stageMatrix, stageRisei = self._getStageMatrix(seeds)
        seedValues = self._getValues((ConvertionMatrix,ConstStageMatrix,stageMatrix),[ConvertionRisei,ConstStageRisei,stageRisei])
        stageValues = self._getStageValues(seedValues)

        name_to_Value = {self.ValueTarget[x]:seedValues[x] for x in range(self.TotalCount)}
        
        print("*******計算結果*********")
        print("基準マップ一覧:",{self.stage_Category_keys[x]:self._seed2StageName(seeds)[x] for x in range(stages_need)})
        print("理性価値一覧:",name_to_Value)
        print("各マップの理性効率:",{self.stageId_to_name[key]:value for key,value in stageValues.items()})
        
        sorted_stageValues = sorted(stageValues.items(),key=lambda x:x[1],reverse=True)
        #print(sorted_stageValues)
        print("カテゴリ別効率順:")
        for category in self.stage_Category_keys:
            print(category + ":")
            stage_toPrint = [x for x in sorted_stageValues if x[0] in self.stage_Category_dict[category]["ValidIds"]]
            targetItemIndex = [self.ValueTarget.index(x) for x in self.stage_Category_dict[category]["Items"]]
            targetItemValues = seedValues[targetItemIndex]
            exclude_Videos_Values = seedValues[4:]
            for item in stage_toPrint:
                print("マップ名:",self.stageId_to_name[item[0]])
                print("最小試行数:",self.stage_dict[item[0]]["minTimes"])
                print("理性消費:",self.stage_dict[item[0]]["apCost"])
                print("理性効率:",item[1])
                print("主素材効率:",np.dot(targetItemValues,self.stage_dict[item[0]]["array"][targetItemIndex])/self.stage_dict[item[0]]["apCost"])
                print("昇進効率:",np.dot(exclude_Videos_Values,self.stage_dict[item[0]]["array"][4:])/self.stage_dict[item[0]]["apCost"])
                #print(targetItemValues)
                #print(self.stage_dict[item[0]]["array"][targetItemIndex])
            print("********************************")
        #資格証効率計算
        #初級資格証
        Item_rarity2 = [
            '固源岩组','全新装置','聚酸酯组', 
            '糖组','异铁组','酮凝集组',
            '扭转醇','轻锰矿','研磨石',
            'RMA70-12','凝胶','炽合金',
            '晶体元件'
        ]
        ticket_efficiency2 = {x:name_to_Value[x]/Price[x] for x in Item_rarity2}
        ticket_efficiency2_sorted = {key:value for key,value in sorted(ticket_efficiency2.items(),key=lambda x:x[1],reverse=True)}
        print("初級資格証効率：",ticket_efficiency2_sorted)
        #上級資格証
        Item_rarity3 = [
            '提纯源岩','改量装置','聚酸酯块', 
            '糖聚块','异铁块','酮阵列', 
            '白马醇','三水锰矿','五水研磨石',
            'RMA70-24','聚合凝胶','炽合金块',
            '晶体电路'
        ]
        ticket_efficiency3 = {x:name_to_Value[x]/Price[x] for x in Item_rarity3}
        ticket_efficiency3_sorted = {key:value for key,value in sorted(ticket_efficiency3.items(),key=lambda x:x[1],reverse=True)}
        print("上級資格証効率：",ticket_efficiency3_sorted)
        

        #メインデータの書き出し
        Columns_Name = self.ValueTarget + ['理性消費']
        Rows_Name_Convertion = ['経験値換算1','経験値換算2','経験値換算3','純金換算'] +\
            ['合成-'+x['name'] for x in self.formula] +\
            ['スキル本換算1','スキル本換算2']
        Rows_Name_ConstStage = ['LS-5','CE-5','CA-5']
        Rows_Name_Stages = [self.stage_Category_keys[x] + self._seed2StageName(seeds)[x] for x in range(stages_need)]
        Rows_Name = Rows_Name_Convertion+Rows_Name_ConstStage+Rows_Name_Stages + ['理性価値']
        #print(Columns_Name)
        #print(Rows_Name)
        main_data = np.vstack((ConvertionMatrix,ConstStageMatrix,stageMatrix,seedValues))
        main_data = np.hstack((main_data,np.concatenate([ConvertionRisei,ConstStageRisei,stageRisei,[0]]).reshape(-1,1)))
        df = pd.DataFrame(main_data,columns=Columns_Name,index=Rows_Name)
        df.to_csv('BaseStages.csv',encoding='utf-8-sig')
        print("基準マップデータをBaseStages.csvに保存しました")

def main():
    rc = RiseiCalculator(minTimes=1000)
    rc.Calc()
    #print(rc.convert_rules)

if __name__=="__main__":
    main()


import json
import re
from openai import OpenAI
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

csv_path = "人事情報.csv"
load_dotenv()
openai_key= os.getenv("OPENAI_API")

df = pd.read_csv(csv_path)
"""
print(df.head())
   id                                                url
0   1  https://global.nissannews.com/ja-JP/releases/2...
1   2     https://news.panasonic.com/jp/press/jn211210-1
2   3  https://global.toyota/jp/newsroom/corporate/36...
3   4  https://sei.co.jp/company/press/personnel-affa...
4   5    https://global.canon/ja/news/2021/20210330.html
"""

def get_html(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text,'html.parser')
    
    if(soup.find_all('table')):
        nor_text = ""
        #v1
        for table in soup.find_all('table'): nor_text += str(table)

        #v2
        # nor_text = ' '.join([table.get_text(separator=' ', strip=True) for table in soup.find_all('table')])
        return nor_text
    else:
        human_datas = soup.find_all(string=lambda text: "人事" in text)
        #v1
        nor_text = ""
        for data in human_datas:
            parent = data.find_parent()
            nor_text += str(parent)
        
        #v2
        # nor_text = ' '.join([data.find_parent().get_text(separator=' ', strip=True) for data in human_datas])

        return nor_text

def analysis(question):
    client = OpenAI(
        api_key=openai_key
    )
    res = client.chat.completions.create(
            messages=[
                {
                    "role":"system",
                    "content":f"""
                    人事情報の解析を行います。
                    解析して各人物の「名前」、「現在の役職」、「新しい役職」を解析して
                    下記のようなjson形式でまとめてください。
                    json形式の例
                    [
                        {{
                            "name":"名前",
                            "former_postion":"現在の役職",
                            "new_position":"新しい役職",
                        }},
                        {{
                            "name":"名前",
                            "former_postion":"現在の役職",
                            "new_position":"新しい役職",
                        }},
                        ...
                    ]
                    """
                },
                {
                    "role":"user",
                    "content":question,
                }
            ],
            model="gpt-4-0125-preview",
    )
    return res

def extraction(message):
    json_pattern = r'\[\n\s*{\n[^]]+\n\s*}\n]'
    matches = re.findall(json_pattern, message, re.DOTALL)
    json_datas = []
    error_datas = []
    for i,match in enumerate(matches):
        try:
            json_data = json.loads(match)
            for j in json_data:
                json_datas.append([i,j])
        except json.JSONDecodeError as e:
            error_datas.append([i,match])

    return (json_datas, error_datas)

def main():
    data = []

    error = []
    for i,url in enumerate(df["url"]):
        print(f"{url = }")
        human_info = get_html(url)
        res = analysis(human_info)
        json_datas,error_datas = extraction(res.choices[0].message.content)
        for json_data in json_datas:
            print(json_data[1])
            data.append(
                {
                    "id":i+1,
                    "url":url,
                    "name":json_data[1]["name"],
                    "former_postion":json_data[1]["former_postion"],
                    "new_position":json_data[1]["new_position"]
                }
            )
        for error_data in error_datas:
            error.append(
                {
                    "id":i+1,
                    "url":url,
                    "error":error_data[1]
                }
            )
    return data,error
data,error = main()
with open("人事情報v1.json", "w",encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

with open("エラー情報v1.json", "w",encoding='utf-8') as f:
    json.dump(error, f, indent=4, ensure_ascii=False)
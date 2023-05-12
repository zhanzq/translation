# !/usr/bin/env python
# encoding=utf-8
# author: zhanzq
# email : zhanzhiqiang09@126.com 
# date  : 2023/5/12
#


# 导入需要的包
import re
import html
from urllib import parse
import requests
import hashlib

import random
import json
import time
from common_utils.text_io.txt import load_from_json, save_to_json


class Translate:
    def __init__(self, tries=3, sleep_time=3):
        self.tries = tries
        self.sleep_time = sleep_time

    def translate_single_sentence_youdao(self, sentence, sl="en", tl="zh-CN", tries=0):
        time.sleep(self.sleep_time)
        # 有道词典 api
        url = 'http://fanyi.youdao.com/translate?smartresult=dict&smartresult=rule&smartresult=ugc&sessionFrom=null'
        # 传输的参数，其中 i 为需要翻译的内容
        key = {
            'type': "AUTO",
            'i': sentence,
            "doctype": "json",
            "version": "2.1",
            "keyfrom": "fanyi.web",
            "ue": "UTF-8",
            "action": "FY_BY_CLICKBUTTON",
            "typoResult": "true"
        }
        try:
            # key 这个字典为发送给有道词典服务器的内容
            response = requests.post(url, data=key)
            # 判断服务器是否相应成功
            if response.status_code == 200:
                # 然后相应的结果
                result = json.loads(response.text)
                result = result['translateResult'][0][0]['tgt']
                return result
            else:
                print("有道词典调用失败")
                # 相应失败就返回空
                return None
        except:
            tries += 1
            if tries >= self.tries:
                return ""
            else:
                return self.translate_single_sentence_youdao(sentence, sl, tl, tries)

    def translate_youdao(self, sentence, sl="en", tl="zh-CN", tries=0):
        chinese = ""
        words = sentence.split(" ")
        if len(words) > 40:
            sentences = sentence.split(". ")
            if not sentences[-1]:
                sentences = sentences[:-1]
            if sentences[-1].endswith("."):
                sentences[-1] = sentences[-1][:-1]
            if len(sentences) > 1:
                sentences = [it + "." for it in sentences]
        else:
            sentences = [sentence]

        for sentence in sentences:
            trans_tmp = self.translate_single_sentence_youdao(sentence, sl, tl, tries)
            if not trans_tmp:
                trans_tmp = sentence
            chinese += trans_tmp

        return chinese

    def translate_google(self, sentence, sl="en", tl="zh-CN", tries=0):
        google_trans_url = 'http://translate.google.com/m?q=%s&sl=%s&tl=%s'
        try:
            time.sleep(self.sleep_time)
            sentence = parse.quote(sentence)
            url = google_trans_url % (sentence, sl, tl)
            response = requests.get(url)
            data = response.text
            expr = r'(?s)class="(?:t0|result-container)">(.*?)<'
            result = re.findall(expr, data)
            if len(result) == 0:
                return ""

            return html.unescape(result[0])
        except:
            tries += 1
            if tries >= 3:
                return ""
            else:
                return self.translate_google(sentence, sl, tl, tries)

    def translate_book(self, input_path, output_path, service="chatGPT"):
        json_obj = load_from_json(input_path)
        idx = 0
        save_frequency = 1 if service == "chatGPT" else 10
        skip_cata_lst = ["References"]
        for cata, paras in json_obj.items():
            if cata in skip_cata_lst:
                continue
            for p_id, it in paras.items():
                source = it["source"]
                if service in it and it[service]:
                    continue
                chinese = ""
                if service == "youdao":
                    chinese = self.translate_youdao(sentence=source)
                elif service == "chatGPT":
                    chinese = self.translate_chatGPT(sentence=source)
                elif service == "google":
                    chinese = self.translate_google(sentence=source)

                it[service] = chinese
                idx += 1

                if idx % save_frequency == 0:
                    save_to_json(json_obj=json_obj, json_path=output_path)

        save_to_json(json_obj=json_obj, json_path=output_path)
        return

    def translate_chatGPT(self, sentence, sl="en", tl="zh-CN", tries=0):
        time.sleep(self.sleep_time)
        lang_map = {
            "en": "英文",
            "zh-CN": "中文",
        }
        url = "https://api.openai.com/v1/chat/completions"

        payload = json.dumps({
          "model": "gpt-3.5-turbo",
          "messages": [
            {
              "role": "user",
              "content": f"{lang_map[sl]}:{sentence}\n{lang_map[tl]}:"
            }
          ]
        })
        headers = {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer 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'
        }

        proxies = {"https": "127.0.0.1:1087"}
        try:
            # 判断服务器是否相应成功
            response = requests.request("POST", url, headers=headers, proxies=proxies, data=payload)
            # 然后相应的结果
            result = json.loads(response.text)
            result = result['choices'][0]['message']["content"]
            return result
        except:
            tries += 1
            if tries > 3:
                print("chatGPT调用失败")
                # 相应失败就返回空
                return None
            else:
                return self.translate_chatGPT(sentence, sl, tl, tries)

    def translate(self, sentence, api="google", sl="en", tl="zh-CN", tries=3):
        tries -= self.tries
        if api == "google":
            return self.translate_google(sentence, sl, tl, tries)
        elif api == "youdao":
            return self.translate_youdao_v3(sentence, sl, tl, tries)
        elif api == "chatGPT":
            return self.translate_chatGPT(sentence, sl, tl, tries)
        else:
            print(f"api={api} not supported currently.")
            return ""

    @staticmethod
    def get_md5(data):
        md5 = hashlib.md5()
        md5.update(data.encode())
        code = md5.hexdigest()
        return code

    @staticmethod
    def get_sign(e, n):
        va = "fanyideskweb"
        la = "Ygy_4c=r#e#4EX^NUGUc5"
        sign = Translate.get_md5(va + e + str(n) + la)

        return sign

    @staticmethod
    def get_sign_info(query):
        version = "5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
        e = query
        bv = t = Translate.get_md5(version)
        ts = o = int(time.time() * 1000)
        salt = n = o + random.randint(0, 10)
        sign = a = Translate.get_sign(e=e, n=n)

        return bv, ts, salt, sign

    def translate_youdao_v3(self, query, sl="en", tl="zh-CHS", tries=0):
        if tl == 'zh-CN':
            tl = "zh-CHS"   # change target language mode
        time.sleep(self.sleep_time)
        youdao_url = 'https://fanyi.youdao.com/bbk/translate_m.do'
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Cookie': '_ga=GA1.2.452896735.1622698877; UM_distinctid=187c1fe1bec18d-0ee785b83fd008-1e525634-1fa400-187c1fe1bedb91; OUTFOX_SEARCH_USER_ID=1645787648@10.108.160.17; SESSION_FROM_COOKIE=mypydict; NTES_YD_SESS=7vZfZLuoBqRE5K9w0noeWOCrIqjr06_DEAwjeCFuGGhfpvFRpWZ9_i_gDEa.aGXmHKhd3cJlVstCVLle6eonu1U5wb5gyqPXqA.zO67Yuei8UOQXNfDsSeTzBkCXS9Oo97ZR81lzG_8qLcbVrM0z59Gmx7PN2gl8FQ9jOM6eBT.1TBntxjjtIha5VgS.pcgykEQtESgHcPKCNN3tSITi1g.dTQSwgtlCLu.OXCG7WrUEN; S_INFO=1683597378|0|0&60##|10000000000; P_INFO=10000000000|1683597378|1|youdao_zhiyun2018|00&99|null&null&null#not_found&null#10#0|&0||10000000000; OUTFOX_SEARCH_USER_ID_NCOO=264906597.95484358; arxivShowTip=true; adcookie=true; download_cookie=true; ___rl__test__cookies=1683873859849',
            'Origin': 'https://fanyi.youdao.com',
            'Referer': 'https://fanyi.youdao.com/index.html',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }

        # zh-CHS
        bv, ts, salt, sign = self.get_sign_info(query)
        payload = f'i={query}&from={sl}&to={tl}&client=fanyideskweb&salt={salt}&sign={sign}&ts={ts}&bv={bv}&doctype=json&version=3.0'

        try:
            resp = requests.request("POST", youdao_url, headers=headers, data=payload)
            chinese = json.loads(resp.text)["translateResult"][1]["tgt"]
            return chinese
        except:
            tries += 1
            if tries > self.tries:
                return ""
            else:
                return self.translate_youdao_v3(query, sl, tl, tries)


def main():
    translator = Translate()
    sentence = "Firstly, for gender and occupation bias, we found that accuracy on the Winogender coreference task improves with model scale, and PaLM 540B sets a new state-of-the-art result in 1-shot and few-shot settings. Secondly, co-occurence analysis performed on race/religion/gender prompt continuation demonstrates the potential for the model to falsely affirm stereotypes, for instance, associating Muslims with terrorism, extremism, and violence."
    youdao_target = translator.translate(sentence, api="youdao")
    print(youdao_target)
    gpt_target = translator.translate(sentence, api="chatGPT")
    print(gpt_target)
    google_target = translator.translate(sentence, api="google")
    print(google_target)

    print(f"input: {sentence}\ngoogle: {google_target}\nyoudao: {youdao_target}\nchatGPT: {gpt_target}")


if __name__ == "__main__":
    main()
